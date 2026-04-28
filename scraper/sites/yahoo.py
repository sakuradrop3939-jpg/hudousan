"""
Yahoo!不動産 中古一戸建て スクレイパー（requests使用）
https://realestate.yahoo.co.jp/
"""
import logging
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper, Property

logger = logging.getLogger(__name__)

BASE = "https://realestate.yahoo.co.jp"

# エリア名 → Yahoo!不動産 パス（実サイトから確認済み）
YAHOO_PATH = {
    "神戸市長田区":  "/used/house/search/06/28/28106/",
    "神戸市兵庫区":  "/used/house/search/06/28/28105/",
    "神戸市北区":    "/used/house/search/06/28/28109/",
    "神戸市垂水区":  "/used/house/search/06/28/28108/",
    "神戸市須磨区":  "/used/house/search/06/28/28107/",
    "兵庫県洲本市":  "/used/house/search/06/28/28205/",
    "徳島県徳島市":  "/used/house/search/08/36/36201/",
    "徳島県小松島市": "/used/house/search/08/36/36203/",
    "徳島県阿南市":  "/used/house/search/08/36/36204/",
    "香川県高松市":  "/used/house/search/08/37/37201/",
    "香川県坂出市":  "/used/house/search/08/37/37203/",
    "香川県丸亀市":  "/used/house/search/08/37/37202/",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9",
}


class YahooScraper(BaseScraper):
    SITE_NAME = "Yahoo不動産"

    def search(self, area: dict) -> list[Property]:
        path = YAHOO_PATH.get(area["name"])
        if not path:
            return []
        results = []
        for pg in range(1, 4):
            pg_url = BASE + path if pg == 1 else BASE + path + f"?page={pg}"
            try:
                time.sleep(2)
                resp = requests.get(pg_url, headers=HEADERS, timeout=20, allow_redirects=True)
                if resp.status_code != 200:
                    break
                soup = BeautifulSoup(resp.text, "lxml")
                cards = soup.select("div.ListCassette2__wrap")
                if not cards:
                    break
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                batch = [p for p in (self._parse_card(c, area, now) for c in cards) if p]
                results.extend(batch)
                if len(batch) < 20:
                    break
            except Exception as e:
                logger.debug("Yahoo %s page%d エラー: %s", area["name"], pg, e)
                break
        logger.info("Yahoo不動産 %s: %d件取得", area["name"], len(results))
        return results

    def _parse_card(self, card, area: dict, now: str) -> Property | None:
        # URL
        link = card.select_one("a[href*='/used/house/']")
        url = link.get("href", "") if link else ""

        # 価格
        price_el = card.select_one("[class*=info__price]")
        price_text = price_el.get_text(strip=True) if price_el else ""
        price_m = re.search(r"([\d,]+)\s*万円", price_text)
        if not price_m:
            return None
        price_man = int(price_m.group(1).replace(",", ""))

        # テキスト全体（住所・間取りを推測）
        text = card.get_text(" ", strip=True)

        # 住所（説明文から推測）
        addr_m = re.search(r"((?:神戸|徳島|高松|坂出|丸亀|洲本).{0,20}?(?:区|市|町|丁目))", text)
        address = addr_m.group(1).strip()[:40] if addr_m else area["name"]

        # 間取り
        layout_m = re.search(r"(\d+(?:LDK|DK|LK|K|SLDK))", text)
        layout = self._normalize_layout(layout_m.group(1)) if layout_m else ""

        # 土地・建物
        land_m = re.search(r"土地[：\s]*([\d.]+)\s*m", text)
        bldg_m = re.search(r"建物[：\s]*([\d.]+)\s*m", text)

        return Property(
            site=self.SITE_NAME,
            name=f"{area['name']} 中古戸建",
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
