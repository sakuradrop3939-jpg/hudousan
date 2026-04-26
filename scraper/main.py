"""
ぼろ戸建て投資物件 自動巡回スクリプト

実行方法:
    python -m scraper.main

出力: docs/index.html → GitHub Pages で公開（完全無料・追加アカウント不要）
"""
import logging
import os
import time
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")

from .config import AREAS, CRITERIA
from .scorer import score, passes_criteria
from .output_html import write_html
from .sites.suumo import SuumoScraper
from .sites.athome import AthomeScraper
from .sites.homes import HomesScraper
from .sites.fudousanjapan import FudousanJapanScraper
from .sites.yahoo import YahooScraper

SCRAPERS = [
    SuumoScraper(),
    AthomeScraper(),
    HomesScraper(),
    FudousanJapanScraper(),
    YahooScraper(),
]


def run():
    logger.info("=" * 60)
    logger.info("巡回開始: %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    logger.info("対象エリア: %d件 / 対象サイト: %d件", len(AREAS), len(SCRAPERS))
    logger.info("=" * 60)

    total_found = 0
    total_passed = 0
    all_records = []

    for scraper in SCRAPERS:
        logger.info("━━ %s 巡回開始 ━━", scraper.SITE_NAME)
        for area in AREAS:
            try:
                props = scraper.search(area)
            except Exception as e:
                logger.error("%s %s: エラー %s", scraper.SITE_NAME, area["name"], e)
                continue

            total_found += len(props)

            for prop in props:
                ok, reason = passes_criteria(prop, CRITERIA)
                if not ok:
                    logger.debug("除外 [%s] %s: %s", prop.site, prop.name[:20], reason)
                    continue

                total_passed += 1
                sr = score(prop, area)
                all_records.append({"prop": prop, "score": sr})

            time.sleep(1.5)

        logger.info("%s 完了", scraper.SITE_NAME)
        time.sleep(3)

    # スコア降順にソート → HTML 生成
    all_records.sort(key=lambda r: r["score"].total, reverse=True)
    html_path = write_html(all_records)

    logger.info("=" * 60)
    logger.info("巡回完了: %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    logger.info("  取得総数:     %d件", total_found)
    logger.info("  条件通過:     %d件", total_passed)
    logger.info("  HTML出力:     %s", html_path)
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
