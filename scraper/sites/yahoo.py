"""
Yahoo!不動産 中古一戸建て スクレイパー
https://realestate.yahoo.co.jp/
JavaScript レンダリングが必要なためPlaywrightを使用。
Playwright未インストール時は requests フォールバック。
"""
import logging
import re
from datetime import datetime

from .base import BaseScraper, Property

logger = logging.getLogger(__name__)

BASE_URL = "https://realestate.yahoo.co.jp/used/house/search/"


class YahooScraper(BaseScraper):
    SITE_NAME = "Yahoo不動産"

    def search(self, area: dict) -> list[Property]:
        try:
            return self._search_playwright(area)
        except Exception as e:
            logger.warning("Yahoo Playwright失敗(%s)。requestsにフォールバック", e)
            return self._search_requests(area)

    def _search_playwright(self, area: dict) -> list[Property]:
        from playwright.sync_api import sync_playwright

        results = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page = context.new_page()

            for pg in range(1, 6):
                url = (
                    f"{BASE_URL}?pref={area['yahoo_pref']}"
                    f"&city={area['yahoo_city']}"
                    f"&pricemax=500"
                    f"&b={pg}"
                )
                try:
                    page.goto(url, timeout=30_000)
                    page.wait_for_selector("[class*='property']", timeout=10_000)
                except Exception:
                    break

                from bs4 import BeautifulSoup
                soup = BeautifulSoup(page.content(), "lxml")
                items = (
                    soup.select("div[class*='property']") or
                    soup.select("li[class*='cassette']") or
                    soup.select("article")
                )
                if not items:
                    break

                batch = []
                for item in items:
                    try:
                        p = self._parse_item(item, area, now)
                        if p:
                            batch.append(p)
                    except Exception as e2:
                        logger.debug("Yahoo parse error: %s", e2)
                results.extend(batch)
                if len(batch) < 20:
                    break

            browser.close()

        logger.info("Yahoo不動産(PW) %s: %d件取得", area["name"], len(results))
        return results

    def _search_requests(self, area: dict) -> list[Property]:
        results = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        for pg in range(1, 4):
            params = {
                "pref": area["yahoo_pref"],
                "city": area["yahoo_city"],
                "pricemax": "500",
                "b": pg,
            }
            soup = self._soup(BASE_URL, params=params)
            if soup is None:
                break
            items = (
                soup.select("div[class*='property']") or
                soup.select("li[class*='cassette']") or
                soup.select("article")
            )
            if not items:
                break
            batch = []
            for item in items:
                try:
                    p = self._parse_item(item, area, now)
                    if p:
                        batch.append(p)
                except Exception:
                    pass
            results.extend(batch)
            if len(batch) < 20:
                break
        logger.info("Yahoo不動産(req) %s: %d件取得", area["name"], len(results))
        return results

    def _parse_item(self, item, area: dict, now: str) -> Property | None:
        full_text = item.get_text(" ", strip=True)

        link_el = (
            item.select_one("h2 a") or
            item.select_one("[class*='title'] a") or
            item.select_one("a[href*='/used/house/']")
        )
        if not link_el:
            return None
        name = link_el.get_text(strip=True)
        href = link_el.get("href", "")
        url = f"https://realestate.yahoo.co.jp{href}" if href.startswith("/") else href

        price_el = item.select_one("[class*='price']") or item.select_one("[class*='Price']")
        price_text = price_el.get_text(strip=True) if price_el else ""
        price_yen, price_man = self._parse_price(price_text)
        if price_yen == 0:
            return None

        addr_el = item.select_one("[class*='address']") or item.select_one("[class*='Address']")
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
