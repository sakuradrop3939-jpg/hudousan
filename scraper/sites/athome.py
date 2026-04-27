"""
アットホーム 中古一戸建て スクレイパー（Playwright使用）
https://www.athome.co.jp/
"""
import logging
import re
from datetime import datetime

from .base import BaseScraper, Property

logger = logging.getLogger(__name__)

BASE = "https://www.athome.co.jp"

# エリア名 → athome パス（実サイトから確認済み）
ATHOME_PATH = {
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


class AthomeScraper(BaseScraper):
    SITE_NAME = "アットホーム"

    def search(self, area: dict) -> list[Property]:
        path = ATHOME_PATH.get(area["name"])
        if not path:
            return []
        try:
            return self._search_playwright(area, path)
        except Exception as e:
            logger.warning("athome Playwright失敗(%s): %s", area["name"], e)
            return []

    def _search_playwright(self, area: dict, path: str) -> list[Property]:
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup

        results = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        url = BASE + path

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="ja-JP",
            )
            page = ctx.new_page()

            for pg in range(1, 4):
                pg_url = url if pg == 1 else f"{url}?page={pg}"
                try:
                    page.goto(pg_url, timeout=30_000, wait_until="domcontentloaded")
                    page.wait_for_timeout(2000)
                except Exception:
                    break

                soup = BeautifulSoup(page.content(), "lxml")
                items = self._find_items(soup)
                if not items:
                    break

                batch = [p for p in (self._parse_item(i, area, now) for i in items) if p]
                results.extend(batch)
                if len(batch) < 20:
                    break

            browser.close()

        logger.info("athome %s: %d件取得", area["name"], len(results))
        return results

    def _find_items(self, soup):
        for sel in [
            "div[class*=property-item]",
            "li[class*=property]",
            "div[class*=bukken]",
            "article",
            "div[class*=cassette]",
        ]:
            items = [i for i in soup.select(sel) if len(i.get_text(strip=True)) > 50]
            if items:
                return items
        return []

    def _parse_item(self, item, area: dict, now: str) -> Property | None:
        text = item.get_text(" ", strip=True)
        if len(text) < 30:
            return None

        # URL
        link = item.select_one("a[href*='/kodate/']") or item.select_one("a[href]")
        href = link.get("href", "") if link else ""
        url = BASE + href if href.startswith("/") else href

        # 価格
        price_m = re.search(r'([\d,]+)\s*万円', text)
        if not price_m:
            return None
        price_man = int(price_m.group(1).replace(",", ""))
        price_yen = price_man * 10_000

        # 住所
        addr_m = re.search(r'(?:所在地|住所)[：\s]*(.+?)(?:間取|築|土地|$)', text)
        address = addr_m.group(1).strip()[:40] if addr_m else area["name"]

        # 間取り
        layout_m = re.search(r'(\d+(?:LDK|DK|LK|K|SLDK))', text)
        layout = self._normalize_layout(layout_m.group(1)) if layout_m else ""

        # 土地・建物
        land_m = re.search(r'土地[：\s]*([\d.]+)\s*m', text)
        bldg_m = re.search(r'建物[：\s]*([\d.]+)\s*m', text)
        land_area = float(land_m.group(1)) if land_m else 0.0
        building_area = float(bldg_m.group(1)) if bldg_m else 0.0

        build_age = self._parse_age(text)
        build_year = self._parse_build_year(text)

        name_el = item.select_one("h2, h3, [class*=title]")
        name = name_el.get_text(strip=True)[:40] if name_el else f"{area['name']} 中古戸建"

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
