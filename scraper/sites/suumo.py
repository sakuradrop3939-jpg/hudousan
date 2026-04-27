"""
SUUMO 中古一戸建て スクレイパー
requests + session（トップページでクッキー取得してから検索）
"""
import logging
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper, Property

logger = logging.getLogger(__name__)

BASE = "https://suumo.jp"
TOP_URL = "https://suumo.jp/"

# エリア名 → SUUMO の sc コード（実サイトから確認済み）
SUUMO_SC = {
    "神戸市長田区":  "/chukoikkodate/hyogo/sc_kobeshinagata/",
    "神戸市兵庫区":  "/chukoikkodate/hyogo/sc_kobeshihyogo/",
    "神戸市北区":    "/chukoikkodate/hyogo/sc_kobeshikita/",
    "神戸市垂水区":  "/chukoikkodate/hyogo/sc_kobeshitarumi/",
    "神戸市須磨区":  "/chukoikkodate/hyogo/sc_kobeshisuma/",
    "兵庫県洲本市":  "/chukoikkodate/hyogo/sc_sumoto/",
    "徳島県徳島市":  "/chukoikkodate/tokushima/sc_tokushima/",
    "徳島県小松島市": "/chukoikkodate/tokushima/sc_komatsushima/",
    "徳島県阿南市":  "/chukoikkodate/tokushima/sc_anan/",
    "香川県高松市":  "/chukoikkodate/kagawa/sc_takamatsu/",
    "香川県坂出市":  "/chukoikkodate/kagawa/sc_sakaide/",
    "香川県丸亀市":  "/chukoikkodate/kagawa/sc_marugame/",
}


class SuumoScraper(BaseScraper):
    SITE_NAME = "SUUMO"
    REQUEST_DELAY = (2.5, 4.0)

    def __init__(self):
        super().__init__()
        self._session_ready = False

    def _ensure_session(self):
        if not self._session_ready:
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ja,en-US;q=0.9",
                "Referer": "https://suumo.jp/",
            })
            try:
                self.session.get(TOP_URL, timeout=15)
                time.sleep(2)
                self._session_ready = True
            except Exception as e:
                logger.warning("SUUMO セッション初期化失敗: %s", e)

    def search(self, area: dict) -> list[Property]:
        sc_path = SUUMO_SC.get(area["name"])
        if not sc_path:
            logger.warning("SUUMO: %s のURLが未定義", area["name"])
            return []

        self._ensure_session()
        results = []
        page = 1

        while page <= 5:
            props = self._fetch_page(area, sc_path, page)
            if not props:
                break
            results.extend(props)
            if len(props) < 20:
                break
            page += 1
            time.sleep(2)

        logger.info("SUUMO %s: %d件取得", area["name"], len(results))
        return results

    def _fetch_page(self, area: dict, sc_path: str, page: int) -> list[Property]:
        url = BASE + sc_path
        params = {"page": page} if page > 1 else {}
        resp = self._get(url, params=params)
        if resp is None:
            return []

        soup = BeautifulSoup(resp.text, "lxml")

        # 物件カード: div.property_unit-content 内に cassette がある
        containers = soup.select("div.property_unit-content")
        if not containers:
            # fallback
            containers = soup.select("div.dottable--cassette")

        if not containers:
            logger.debug("SUUMO %s page%d: 物件なし (html_len=%d)", area["name"], page, len(resp.text))
            return []

        props = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        for container in containers:
            try:
                p = self._parse_container(container, area, now)
                if p:
                    props.append(p)
            except Exception as e:
                logger.debug("SUUMO parse error: %s", e)
        return props

    def _parse_container(self, container, area: dict, now: str) -> Property | None:
        text = container.get_text(" ", strip=True)

        # URL（nc_ を含むリンク）
        link = container.select_one("a[href*='nc_']")
        if not link:
            # 親要素からも探す
            parent = container.parent
            if parent:
                link = parent.select_one("a[href*='nc_']")
        url = BASE + link.get("href") if link else ""

        # 物件名
        name_el = container.select_one("h2, .property_unit-title, [class*=title]")
        name = name_el.get_text(strip=True) if name_el else re.search(r'物件名\s*(.+?)(?:販売|$)', text)
        if hasattr(name, 'group'):
            name = name.group(1).strip()[:40] if name else area["name"] + " 中古戸建"
        elif not isinstance(name, str):
            name = area["name"] + " 中古戸建"

        # 販売価格
        price_m = re.search(r'販売価格\s*([\d,]+)万円', text)
        if not price_m:
            price_m = re.search(r'([\d,]+)万円', text)
        if not price_m:
            return None
        price_man = int(price_m.group(1).replace(",", ""))
        price_yen = price_man * 10_000

        # 所在地
        addr_m = re.search(r'所在地\s*(.+?)(?:沿線|駅|$)', text)
        address = addr_m.group(1).strip()[:40] if addr_m else area["name"]

        # 間取り
        layout_m = re.search(r'間取り\s*(\d+[A-Za-z]+(?:\+[A-Za-z]+)?)', text)
        layout = self._normalize_layout(layout_m.group(1)) if layout_m else ""

        # 土地面積
        land_m = re.search(r'土地面積\s*([\d.]+)', text)
        land_area = float(land_m.group(1)) if land_m else 0.0

        # 建物面積
        bldg_m = re.search(r'建物面積\s*([\d.]+)', text)
        building_area = float(bldg_m.group(1)) if bldg_m else 0.0

        # 築年
        build_m = re.search(r'築年月\s*(\d{4})年', text)
        build_year = int(build_m.group(1)) if build_m else 0
        build_age = (datetime.now().year - build_year) if build_year else 0

        return Property(
            site=self.SITE_NAME,
            name=name,
            url=url,
            address=address,
            area_name=area["name"],
            price=price_yen,
            price_man=price_man,
            layout=layout,
            land_area=land_area,
            building_area=building_area,
            building_year=build_year,
            building_age=build_age,
            parking=self._detect_parking(text),
            rebuild_ok=self._detect_rebuild(text),
            sewage=self._detect_sewage(text),
            fetched_at=now,
        )
