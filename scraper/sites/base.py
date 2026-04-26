"""
全サイト共通の基底スクレイパークラス
"""
import re
import time
import random
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

_ua = UserAgent()


@dataclass
class Property:
    site: str = ""
    name: str = ""
    url: str = ""
    address: str = ""
    area_name: str = ""
    price: int = 0               # 円
    price_man: int = 0           # 万円
    layout: str = ""             # 3LDK など
    land_area: float = 0.0       # 土地㎡
    building_area: float = 0.0   # 建物㎡
    building_year: int = 0       # 建築年（西暦）
    building_age: int = 0        # 築年数
    parking: Optional[bool] = None   # None=不明
    rebuild_ok: Optional[bool] = None
    sewage: Optional[bool] = None
    fetched_at: str = ""
    raw: dict = field(default_factory=dict)

    def dedup_key(self) -> str:
        """重複判定キー：URLがある場合はURL、なければ住所＋価格＋間取り"""
        if self.url:
            # クエリパラメータを除いた正規化URL
            return re.sub(r'\?.*$', '', self.url)
        return f"{self.address}|{self.price}|{self.layout}"


class BaseScraper(ABC):
    SITE_NAME = "Unknown"
    REQUEST_DELAY = (2.0, 4.0)  # 秒（min, max）

    def __init__(self):
        self.session = requests.Session()
        self._reset_headers()

    def _reset_headers(self):
        self.session.headers.update({
            "User-Agent": _ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        })

    def _get(self, url: str, params: dict = None, retries: int = 3) -> Optional[requests.Response]:
        delay = random.uniform(*self.REQUEST_DELAY)
        time.sleep(delay)
        for attempt in range(retries):
            try:
                resp = self.session.get(url, params=params, timeout=30)
                if resp.status_code == 200:
                    return resp
                if resp.status_code in (403, 429):
                    logger.warning("%s: %s → status %s, retry %d", self.SITE_NAME, url, resp.status_code, attempt + 1)
                    time.sleep(10 * (attempt + 1))
                    self._reset_headers()
            except requests.RequestException as e:
                logger.warning("%s: request error %s (attempt %d)", self.SITE_NAME, e, attempt + 1)
                time.sleep(5)
        return None

    def _soup(self, url: str, params: dict = None) -> Optional[BeautifulSoup]:
        resp = self._get(url, params=params)
        if resp is None:
            return None
        return BeautifulSoup(resp.text, "lxml")

    # ── テキストパーサーユーティリティ ──────────────

    @staticmethod
    def _parse_price(text: str) -> tuple[int, int]:
        """'350万円' → (3_500_000, 350)"""
        if not text:
            return 0, 0
        text = text.replace(",", "").replace(" ", "").replace("　", "")
        m = re.search(r'(\d+(?:\.\d+)?)\s*万', text)
        if m:
            man = float(m.group(1))
            return int(man * 10_000), int(man)
        m = re.search(r'(\d{6,})', text)
        if m:
            yen = int(m.group(1))
            return yen, yen // 10_000
        return 0, 0

    @staticmethod
    def _parse_area(text: str) -> float:
        """'100.50m²' / '100.50㎡' → 100.5"""
        if not text:
            return 0.0
        m = re.search(r'([\d,]+(?:\.\d+)?)\s*(?:㎡|m²|m2|平米)', text)
        if m:
            return float(m.group(1).replace(",", ""))
        return 0.0

    @staticmethod
    def _parse_age(text: str) -> int:
        """'築25年' / '1985年築' / '1985年建築' → 築年数"""
        import datetime
        if not text:
            return 0
        m = re.search(r'築(\d+)年', text)
        if m:
            return int(m.group(1))
        m = re.search(r'(\d{4})\s*年\s*(?:築|建築|建|竣工)', text)
        if m:
            return datetime.date.today().year - int(m.group(1))
        m = re.search(r'(\d{4})', text)
        if m:
            year = int(m.group(1))
            if 1900 < year <= datetime.date.today().year:
                return datetime.date.today().year - year
        return 0

    @staticmethod
    def _parse_build_year(text: str) -> int:
        """'1985年築' → 1985"""
        if not text:
            return 0
        m = re.search(r'(\d{4})\s*年', text)
        if m:
            return int(m.group(1))
        return 0

    @staticmethod
    def _detect_parking(text: str) -> Optional[bool]:
        if not text:
            return None
        t = text.lower()
        if any(kw in t for kw in ["駐車場あり", "駐車場：あり", "駐車1台", "駐車2台", "車庫あり", "ガレージ", "造成可"]):
            return True
        if any(kw in t for kw in ["駐車場なし", "駐車場：なし", "駐車不可"]):
            return False
        return None

    @staticmethod
    def _detect_rebuild(text: str) -> Optional[bool]:
        if not text:
            return None
        if "再建築不可" in text:
            return False
        if "再建築可" in text:
            return True
        return None

    @staticmethod
    def _detect_sewage(text: str) -> Optional[bool]:
        if not text:
            return None
        if any(kw in text for kw in ["公共下水", "下水道接続", "下水：あり", "下水あり"]):
            return True
        if any(kw in text for kw in ["汲み取り", "浄化槽", "下水道未"]):
            return False
        return None

    @staticmethod
    def _normalize_layout(text: str) -> str:
        """'3LDK+S' / '３ＬＤＫ' を正規化"""
        if not text:
            return ""
        text = text.strip()
        # 全角→半角
        text = text.translate(str.maketrans(
            "０１２３４５６７８９ＬＤＫＳＲＴＵＷＡＢＣＤＥＦＧＨＩＪＫＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ",
            "0123456789LDKSRTUWABCDEFGHIJKMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        ))
        m = re.search(r'\d+[A-Z]+(?:\+[A-Z]+)?', text.upper())
        return m.group(0) if m else text

    @abstractmethod
    def search(self, area: dict) -> list[Property]:
        """指定エリアを検索し Property リストを返す"""
        ...
