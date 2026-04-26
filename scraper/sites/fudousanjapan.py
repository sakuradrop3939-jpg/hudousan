"""
不動産ジャパン 中古一戸建て スクレイパー
https://www.fudousan.or.jp/
"""
import logging
import re
from datetime import datetime

from .base import BaseScraper, Property

logger = logging.getLogger(__name__)

BASE_URL = "https://www.fudousan.or.jp/property/buy/house/list/"


class FudousanJapanScraper(BaseScraper):
    SITE_NAME = "不動産ジャパン"

    def search(self, area: dict) -> list[Property]:
        results = []
        page = 1
        while page <= 5:
            props = self._fetch_page(area, page)
            if not props:
                break
            results.extend(props)
            if len(props) < 20:
                break
            page += 1
        logger.info("不動産ジャパン %s: %d件取得", area["name"], len(results))
        return results

    def _fetch_page(self, area: dict, page: int) -> list[Property]:
        params = {
            "pref": area["pref_code"],
            "city": area["city_code"],
            "priceMax": "500",
            "page": page,
        }
        soup = self._soup(BASE_URL, params=params)
        if soup is None:
            return []

        items = (
            soup.select("div[class*='property-item']") or
            soup.select("div[class*='bukken-item']") or
            soup.select("li[class*='property']") or
            soup.select("article")
        )
        if not items:
            return []

        props = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        for item in items:
            try:
                p = self._parse_item(item, area, now)
                if p:
                    props.append(p)
            except Exception as e:
                logger.debug("不動産ジャパン parse error: %s", e)
        return props

    def _parse_item(self, item, area: dict, now: str) -> Property | None:
        full_text = item.get_text(" ", strip=True)

        link_el = (
            item.select_one("h2 a") or
            item.select_one("h3 a") or
            item.select_one("[class*='title'] a") or
            item.select_one("a[href*='/property/']")
        )
        if not link_el:
            return None
        name = link_el.get_text(strip=True)
        href = link_el.get("href", "")
        url = f"https://www.fudousan.or.jp{href}" if href.startswith("/") else href

        price_el = item.select_one("[class*='price']")
        price_text = price_el.get_text(strip=True) if price_el else ""
        price_yen, price_man = self._parse_price(price_text)
        if price_yen == 0:
            return None

        addr_el = item.select_one("[class*='address']") or item.select_one("[class*='location']")
        address = addr_el.get_text(strip=True) if addr_el else area["name"]

        m = re.search(r'\d+(?:LDK|DK|LK|K|SLDK|SDK)', full_text)
        layout = self._normalize_layout(m.group(0) if m else "")

        m_land = re.search(r'土地[面積：\s]*([\d.]+)\s*㎡', full_text)
        m_bldg = re.search(r'建物[面積：\s]*([\d.]+)\s*㎡', full_text)
        land_area = float(m_land.group(1)) if m_land else 0.0
        building_area = float(m_bldg.group(1)) if m_bldg else 0.0

        building_age = self._parse_age(full_text)
        building_year = self._parse_build_year(full_text)

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
            building_year=building_year,
            building_age=building_age,
            parking=self._detect_parking(full_text),
            rebuild_ok=self._detect_rebuild(full_text),
            sewage=self._detect_sewage(full_text),
            fetched_at=now,
        )
