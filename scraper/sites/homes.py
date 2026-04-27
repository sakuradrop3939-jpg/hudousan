"""
LIFULL HOME'S 中古一戸建て スクレイパー（requests + session）
https://www.homes.co.jp/
"""
import logging
import re
import time
from datetime import datetime

from bs4 import BeautifulSoup

from .base import BaseScraper, Property

logger = logging.getLogger(__name__)

BASE = "https://www.homes.co.jp"
TOP_URL = "https://www.homes.co.jp/"

# エリア名 → homes パス（実サイトから確認済み）
HOMES_PATH = {
    "神戸市長田区":  "/kodate/chuko/hyogo/kobe_nagata-city/list/",
    "神戸市兵庫区":  "/kodate/chuko/hyogo/kobe_hyogo-city/list/",
    "神戸市北区":    "/kodate/chuko/hyogo/kobe_kita-city/list/",
    "神戸市垂水区":  "/kodate/chuko/hyogo/kobe_tarumi-city/list/",
    "神戸市須磨区":  "/kodate/chuko/hyogo/kobe_suma-city/list/",
    "兵庫県洲本市":  "/kodate/chuko/hyogo/sumoto-city/list/",
    "徳島県徳島市":  "/kodate/chuko/tokushima/tokushima-city/list/",
    "徳島県小松島市": "/kodate/chuko/tokushima/komatsushima-city/list/",
    "徳島県阿南市":  "/kodate/chuko/tokushima/anan-city/list/",
    "香川県高松市":  "/kodate/chuko/kagawa/takamatsu-city/list/",
    "香川県坂出市":  "/kodate/chuko/kagawa/sakaide-city/list/",
    "香川県丸亀市":  "/kodate/chuko/kagawa/marugame-city/list/",
}


class HomesScraper(BaseScraper):
    SITE_NAME = "ホームズ"
    REQUEST_DELAY = (2.0, 3.5)

    def __init__(self):
        super().__init__()
        self._session_ready = False

    def _ensure_session(self):
        if not self._session_ready:
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ja,en-US;q=0.9",
                "Referer": "https://www.homes.co.jp/",
            })
            try:
                self.session.get(TOP_URL, timeout=15)
                time.sleep(1.5)
                self._session_ready = True
            except Exception as e:
                logger.warning("homes セッション初期化失敗: %s", e)

    def search(self, area: dict) -> list[Property]:
        path = HOMES_PATH.get(area["name"])
        if not path:
            return []

        self._ensure_session()
        results = []

        for page in range(1, 4):
            props = self._fetch_page(area, path, page)
            if not props:
                break
            results.extend(props)
            if len(props) < 20:
                break
            time.sleep(2)

        logger.info("ホームズ %s: %d件取得", area["name"], len(results))
        return results

    def _fetch_page(self, area: dict, path: str, page: int) -> list[Property]:
        url = BASE + path
        params = {"page": page} if page > 1 else {}
        resp = self._get(url, params=params)
        if resp is None or resp.status_code not in (200, 202):
            return []

        soup = BeautifulSoup(resp.text, "lxml")

        items = []
        for sel in ["div[class*=mod-mergeBuilding]", "div[class*=imod-building]",
                    "li[class*=property]", "div[class*=cassette]", "article"]:
            candidates = [i for i in soup.select(sel) if len(i.get_text(strip=True)) > 50]
            if candidates:
                items = candidates
                break

        if not items:
            return []

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        props = []
        for item in items:
            try:
                p = self._parse_item(item, area, now)
                if p:
                    props.append(p)
            except Exception as e:
                logger.debug("homes parse error: %s", e)
        return props

    def _parse_item(self, item, area: dict, now: str) -> Property | None:
        text = item.get_text(" ", strip=True)
        if len(text) < 30:
            return None

        link = item.select_one("a[href*='/kodate/']") or item.select_one("a[href]")
        href = link.get("href", "") if link else ""
        url = BASE + href if href.startswith("/") else href

        price_m = re.search(r'([\d,]+)万円', text)
        if not price_m:
            return None
        price_man = int(price_m.group(1).replace(",", ""))

        addr_m = re.search(r'(?:所在地|住所)[：\s]*(.+?)(?:間取|築|土地|$)', text)
        address = addr_m.group(1).strip()[:40] if addr_m else area["name"]

        layout_m = re.search(r'(\d+(?:LDK|DK|LK|K|SLDK))', text)
        layout = self._normalize_layout(layout_m.group(1)) if layout_m else ""

        land_m = re.search(r'土地[：\s]*([\d.]+)\s*m', text)
        bldg_m = re.search(r'建物[：\s]*([\d.]+)\s*m', text)

        name_el = item.select_one("h2, h3, [class*=title]")
        name = name_el.get_text(strip=True)[:40] if name_el else f"{area['name']} 中古戸建"

        return Property(
            site=self.SITE_NAME,
            name=name,
            url=url,
            address=address,
            area_name=area["name"],
            price=price_man * 10_000,
            price_man=price_man,
            layout=layout,
            land_area=float(land_m.group(1)) if land_m else 0.0,
            building_area=float(bldg_m.group(1)) if bldg_m else 0.0,
            building_year=self._parse_build_year(text),
            building_age=self._parse_age(text),
            parking=self._detect_parking(text),
            rebuild_ok=self._detect_rebuild(text),
            sewage=self._detect_sewage(text),
            fetched_at=now,
        )
