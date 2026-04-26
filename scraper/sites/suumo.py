"""
SUUMO 中古一戸建て スクレイパー
https://suumo.jp/
"""
import logging
import re
from datetime import datetime

from .base import BaseScraper, Property

logger = logging.getLogger(__name__)

BASE_URL = "https://suumo.jp/jj/bukken/ichiran/JJ010FJ001/"


class SuumoScraper(BaseScraper):
    SITE_NAME = "SUUMO"

    def search(self, area: dict) -> list[Property]:
        results = []
        page = 1
        while True:
            props = self._fetch_page(area, page)
            if not props:
                break
            results.extend(props)
            if len(props) < 20:  # 最終ページ（件数が少ない）
                break
            if page >= 5:        # 安全上限
                break
            page += 1
        logger.info("SUUMO %s: %d件取得", area["name"], len(results))
        return results

    def _fetch_page(self, area: dict, page: int) -> list[Property]:
        params = {
            "ar": area["suumo_ar"],
            "bs": "011",           # 中古一戸建て
            "ta": area["pref_code"],
            "sc": area["city_code"],
            "page": page,
        }
        soup = self._soup(BASE_URL, params=params)
        if soup is None:
            return []

        items = (
            soup.select("div.cassetteitem") or
            soup.select("div[class*='property_unit']") or
            soup.select("li.js-cassette_link")
        )
        if not items:
            logger.debug("SUUMO %s page%d: 物件なし", area["name"], page)
            return []

        props = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        for item in items:
            try:
                p = self._parse_item(item, area, now)
                if p:
                    props.append(p)
            except Exception as e:
                logger.debug("SUUMO parse error: %s", e)
        return props

    def _parse_item(self, item, area: dict, now: str) -> Property | None:
        # ── タイトル・URL ──
        link_el = (
            item.select_one("div.cassetteitem_content-title a") or
            item.select_one(".property_unit-title a") or
            item.select_one("a[href*='/chukoikkodate/']") or
            item.select_one("h2 a") or
            item.select_one("a")
        )
        if not link_el:
            return None
        name = link_el.get_text(strip=True)
        href = link_el.get("href", "")
        url = f"https://suumo.jp{href}" if href.startswith("/") else href

        # ── 価格 ──
        price_el = (
            item.select_one(".cassetteitem_price--contract .price_price") or
            item.select_one(".cassetteitem_price span") or
            item.select_one("[class*='price']")
        )
        price_text = price_el.get_text(strip=True) if price_el else ""
        price_yen, price_man = self._parse_price(price_text)
        if price_yen == 0:
            return None

        # ── 所在地 ──
        addr_el = (
            item.select_one("li.cassetteitem_detail-col1") or
            item.select_one(".cassetteitem_detail .cassette-overview-detail__item:first-child")
        )
        address = addr_el.get_text(strip=True) if addr_el else area["name"]

        # ── 詳細テキスト（全テキスト結合して各項目を判定）──
        full_text = item.get_text(" ", strip=True)

        # ── 間取り ──
        layout_el = item.select_one("[class*='madori']") or item.select_one("[class*='layout']")
        layout_text = layout_el.get_text(strip=True) if layout_el else ""
        if not layout_text:
            m = re.search(r'\d+(?:LDK|DK|LK|K|SLDK|SDK)', full_text)
            layout_text = m.group(0) if m else ""
        layout = self._normalize_layout(layout_text)

        # ── 面積 ──
        land_area = 0.0
        building_area = 0.0
        area_cells = item.select("td") + item.select("dd") + item.select("span")
        for el in area_cells:
            t = el.get_text(strip=True)
            if "土地" in t or "敷地" in t:
                land_area = land_area or self._parse_area(t)
            if "建物" in t or "専有" in t:
                building_area = building_area or self._parse_area(t)
        if land_area == 0:
            m = re.search(r'土地[面積：\s]*([\d.]+)\s*㎡', full_text)
            land_area = float(m.group(1)) if m else 0.0
        if building_area == 0:
            m = re.search(r'建物[面積：\s]*([\d.]+)\s*㎡', full_text)
            building_area = float(m.group(1)) if m else 0.0

        # ── 築年数 ──
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
