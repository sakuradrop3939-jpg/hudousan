"""
Google Spreadsheet 書き込みモジュール
- モバイル最適化（直リンクを先頭列に配置）
- スコアに応じた背景色（緑〜赤グラデーション）
- ヒートマップ列のセル背景色
- 重複書き込み防止（URLベースで判定）
"""
import logging
import os
from typing import Optional

import gspread
from gspread_formatting import (
    CellFormat, Color, TextFormat,
    ConditionalFormatRule, BooleanRule, BooleanCondition,
    GridRange, get_conditional_format_rules, set_conditional_format_rules,
    format_cell_range, format_cell_ranges,
)
from google.oauth2.service_account import Credentials

from .config import SHEET_COLUMNS, SPREADSHEET_TITLE, DEMAND_CELL_COLORS, DEMAND_LABELS

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# 列インデックス（0始まり）
COL = {name: i for i, name in enumerate(SHEET_COLUMNS)}


def _get_client(credentials_path: str) -> gspread.Client:
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    return gspread.authorize(creds)


def get_or_create_spreadsheet(credentials_path: str, spreadsheet_id: Optional[str] = None) -> gspread.Spreadsheet:
    gc = _get_client(credentials_path)
    if spreadsheet_id:
        return gc.open_by_key(spreadsheet_id)
    # IDが未設定なら新規作成
    sh = gc.create(SPREADSHEET_TITLE)
    logger.info("スプレッドシート新規作成: %s", sh.url)
    print(f"\n✅ スプレッドシートを作成しました:\n   {sh.url}")
    print(f"   SPREADSHEET_ID={sh.id}\n   .envに設定してください\n")
    return sh


def setup_worksheet(sh: gspread.Spreadsheet) -> gspread.Worksheet:
    """シートがなければ作成し、ヘッダーと書式を設定する"""
    ws_name = "物件リスト"
    try:
        ws = sh.worksheet(ws_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=ws_name, rows=2000, cols=len(SHEET_COLUMNS))
        _write_headers(ws)
        _apply_formatting(ws)
        logger.info("シート '%s' を初期化", ws_name)
    return ws


def _write_headers(ws: gspread.Worksheet):
    ws.update("A1", [SHEET_COLUMNS], value_input_option="USER_ENTERED")
    fmt = CellFormat(
        backgroundColor=Color(0.20, 0.20, 0.20),
        textFormat=TextFormat(bold=True, foregroundColor=Color(1, 1, 1), fontSize=10),
    )
    format_cell_range(ws, "A1:Q1", fmt)
    ws.freeze(rows=1)


def _apply_formatting(ws: gspread.Worksheet):
    """スコア列の条件付き書式 + 列幅設定"""
    score_col = gspread.utils.rowcol_to_a1(1, COL["スコア/100"] + 1)[0]
    score_range = f"{score_col}2:{score_col}2000"

    rules = [
        # 80〜100点: 濃い緑
        ConditionalFormatRule(
            ranges=[GridRange.from_a1_range(score_range, ws)],
            booleanRule=BooleanRule(
                condition=BooleanCondition("NUMBER_GREATER_THAN_EQ", ["80"]),
                format=CellFormat(
                    backgroundColor=Color(0.18, 0.62, 0.22),
                    textFormat=TextFormat(bold=True, foregroundColor=Color(1, 1, 1)),
                ),
            ),
        ),
        # 65〜79点: 黄緑
        ConditionalFormatRule(
            ranges=[GridRange.from_a1_range(score_range, ws)],
            booleanRule=BooleanRule(
                condition=BooleanCondition("NUMBER_BETWEEN", ["65", "79"]),
                format=CellFormat(backgroundColor=Color(0.72, 0.88, 0.42)),
            ),
        ),
        # 50〜64点: 黄
        ConditionalFormatRule(
            ranges=[GridRange.from_a1_range(score_range, ws)],
            booleanRule=BooleanRule(
                condition=BooleanCondition("NUMBER_BETWEEN", ["50", "64"]),
                format=CellFormat(backgroundColor=Color(1.0, 0.95, 0.40)),
            ),
        ),
        # 49点以下: 薄赤
        ConditionalFormatRule(
            ranges=[GridRange.from_a1_range(score_range, ws)],
            booleanRule=BooleanRule(
                condition=BooleanCondition("NUMBER_LESS_THAN", ["50"]),
                format=CellFormat(backgroundColor=Color(0.95, 0.60, 0.60)),
            ),
        ),
    ]
    set_conditional_format_rules(ws, rules)

    # 列幅（文字数基準）
    ws.spreadsheet.batch_update({
        "requests": [
            _col_width_req(ws, 0, 200),   # 直リンク
            _col_width_req(ws, 1, 80),    # スコア
            _col_width_req(ws, 2, 80),    # 賃貸需要
            _col_width_req(ws, 3, 120),   # エリア
            _col_width_req(ws, 4, 90),    # 価格
            _col_width_req(ws, 5, 80),    # 間取り
            _col_width_req(ws, 6, 340),   # おすすめ理由
            _col_width_req(ws, 7, 70),    # 築年数
            _col_width_req(ws, 8, 70),    # 土地
            _col_width_req(ws, 9, 70),    # 建物
            _col_width_req(ws, 10, 80),   # 駐車場
            _col_width_req(ws, 11, 80),   # 再建築
            _col_width_req(ws, 12, 80),   # 下水道
            _col_width_req(ws, 13, 110),  # 掲載サイト
            _col_width_req(ws, 14, 130),  # 取得日時
            _col_width_req(ws, 15, 180),  # 物件名
            _col_width_req(ws, 16, 200),  # 所在地詳細
        ]
    })


def _col_width_req(ws: gspread.Worksheet, col_idx: int, px: int) -> dict:
    return {
        "updateDimensionProperties": {
            "range": {
                "sheetId": ws.id,
                "dimension": "COLUMNS",
                "startIndex": col_idx,
                "endIndex": col_idx + 1,
            },
            "properties": {"pixelSize": px},
            "fields": "pixelSize",
        }
    }


def get_existing_urls(ws: gspread.Worksheet) -> set[str]:
    """既存の URL 列を読み取り、重複チェック用セットを返す"""
    # 直リンク列から HYPERLINK 式の URL を抽出
    col_a = ws.col_values(1)  # A列 = 直リンク
    urls = set()
    for cell in col_a[1:]:  # ヘッダー除く
        if cell and cell.startswith("=HYPERLINK"):
            import re
            m = re.search(r'HYPERLINK\("([^"]+)"', cell)
            if m:
                urls.add(m.group(1))
        elif cell.startswith("http"):
            urls.add(cell)
    return urls


def write_properties(ws: gspread.Worksheet, records: list[dict]) -> int:
    """
    records: [{"prop": Property, "score": ScoreResult}, ...]
    新規物件のみ書き込み、追加件数を返す
    """
    if not records:
        return 0

    existing_urls = get_existing_urls(ws)
    new_rows = []
    demand_colors_to_set = []  # (row_number, demand_level)

    next_row = len(ws.col_values(1)) + 1  # 次の書き込み行

    for rec in records:
        prop = rec["prop"]
        sr = rec["score"]

        # 重複チェック
        if prop.url and prop.url in existing_urls:
            continue

        dl = DEMAND_LABELS.get(sr.demand_level, DEMAND_LABELS[2])
        demand_text = f"{dl['emoji']} {dl['text']}"

        # 駐車場・再建築・下水道の表示
        parking_str = "あり" if prop.parking is True else ("なし" if prop.parking is False else "不明")
        rebuild_str = "可" if prop.rebuild_ok is True else ("不可" if prop.rebuild_ok is False else "不明")
        sewage_str = "接続済" if prop.sewage is True else ("未" if prop.sewage is False else "不明")

        # 直リンク列: HYPERLINK式（タップで物件ページに飛べる）
        link_formula = f'=HYPERLINK("{prop.url}","物件を見る")' if prop.url else ""

        row = [""] * len(SHEET_COLUMNS)
        row[COL["直リンク"]]       = link_formula
        row[COL["スコア/100"]]     = sr.total
        row[COL["賃貸需要"]]       = demand_text
        row[COL["エリア"]]         = prop.area_name
        row[COL["価格（万円）"]]   = prop.price_man or (prop.price // 10_000)
        row[COL["間取り"]]         = prop.layout
        row[COL["おすすめ理由"]]   = sr.reason
        row[COL["築年数"]]         = f"{prop.building_age}年" if prop.building_age else ""
        row[COL["土地㎡"]]         = prop.land_area or ""
        row[COL["建物㎡"]]         = prop.building_area or ""
        row[COL["駐車場"]]         = parking_str
        row[COL["再建築"]]         = rebuild_str
        row[COL["下水道"]]         = sewage_str
        row[COL["掲載サイト"]]     = prop.site
        row[COL["取得日時"]]       = prop.fetched_at
        row[COL["物件名"]]         = prop.name
        row[COL["所在地詳細"]]     = prop.address

        new_rows.append(row)
        demand_colors_to_set.append((next_row, sr.demand_level))
        next_row += 1

        if prop.url:
            existing_urls.add(prop.url)

    if not new_rows:
        return 0

    # まとめて書き込み
    start_row = next_row - len(new_rows)
    ws.append_rows(new_rows, value_input_option="USER_ENTERED")

    # 賃貸需要セルの背景色を設定
    _apply_demand_colors(ws, demand_colors_to_set)

    # スコア降順に並び替え
    _sort_by_score(ws)

    logger.info("%d件の新規物件をシートに追加", len(new_rows))
    return len(new_rows)


def _apply_demand_colors(ws: gspread.Worksheet, demand_rows: list[tuple[int, int]]):
    """賃貸需要列（C列）の各セルに背景色を設定"""
    demand_col_letter = gspread.utils.rowcol_to_a1(1, COL["賃貸需要"] + 1)[0]
    requests = []
    for row_num, demand_level in demand_rows:
        rgb = DEMAND_CELL_COLORS.get(demand_level, DEMAND_CELL_COLORS[2])
        cell_range = f"{demand_col_letter}{row_num}"
        fmt = CellFormat(backgroundColor=Color(rgb["red"], rgb["green"], rgb["blue"]))
        format_cell_range(ws, cell_range, fmt)


def _sort_by_score(ws: gspread.Worksheet):
    """スコア列（B列）で降順ソート（ヘッダー行を除く）"""
    try:
        ws.spreadsheet.batch_update({
            "requests": [{
                "sortRange": {
                    "range": {
                        "sheetId": ws.id,
                        "startRowIndex": 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": len(SHEET_COLUMNS),
                    },
                    "sortSpecs": [{
                        "dimensionIndex": COL["スコア/100"],
                        "sortOrder": "DESCENDING",
                    }],
                }
            }]
        })
    except Exception as e:
        logger.warning("ソート失敗: %s", e)
