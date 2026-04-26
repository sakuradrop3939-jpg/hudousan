"""
巡回対象エリア・検索条件・スコアリング設定
"""

# ──────────────────────────────────────────────
# 対象エリア定義
# demand_level: 1=低 2=中 3=中高 4=高
# avg_rent: 戸建て月額想定賃料（円）
# ──────────────────────────────────────────────
AREAS = [
    # ── 兵庫県 神戸市 ──
    {
        "name": "神戸市長田区",
        "pref": "兵庫県",
        "pref_code": "28",
        "city_code": "28104",
        "suumo_ar": "050",
        "athome_path": "hyogo/kobeshi/nagata-ku",
        "homes_path": "hyogo/kobe-shi/nagata-ku",
        "yahoo_pref": "28",
        "yahoo_city": "28104",
        "demand_level": 3,
        "avg_rent": 55_000,
        "comment": "JR・山陽電鉄あり。単身〜2人世帯の需要が安定",
    },
    {
        "name": "神戸市兵庫区",
        "pref": "兵庫県",
        "pref_code": "28",
        "city_code": "28103",
        "suumo_ar": "050",
        "athome_path": "hyogo/kobeshi/hyogo-ku",
        "homes_path": "hyogo/kobe-shi/hyogo-ku",
        "yahoo_pref": "28",
        "yahoo_city": "28103",
        "demand_level": 2,
        "avg_rent": 50_000,
        "comment": "下町エリア。安定需要だが競争物件多め",
    },
    {
        "name": "神戸市北区",
        "pref": "兵庫県",
        "pref_code": "28",
        "city_code": "28109",
        "suumo_ar": "050",
        "athome_path": "hyogo/kobeshi/kita-ku",
        "homes_path": "hyogo/kobe-shi/kita-ku",
        "yahoo_pref": "28",
        "yahoo_city": "28109",
        "demand_level": 2,
        "avg_rent": 55_000,
        "comment": "郊外ファミリー層。土地広め物件多い",
    },
    {
        "name": "神戸市垂水区",
        "pref": "兵庫県",
        "pref_code": "28",
        "city_code": "28106",
        "suumo_ar": "050",
        "athome_path": "hyogo/kobeshi/tarumi-ku",
        "homes_path": "hyogo/kobe-shi/tarumi-ku",
        "yahoo_pref": "28",
        "yahoo_city": "28106",
        "demand_level": 3,
        "avg_rent": 60_000,
        "comment": "JR・山陽電鉄あり。ファミリー賃貸需要が高い住環境",
    },
    {
        "name": "神戸市須磨区",
        "pref": "兵庫県",
        "pref_code": "28",
        "city_code": "28105",
        "suumo_ar": "050",
        "athome_path": "hyogo/kobeshi/suma-ku",
        "homes_path": "hyogo/kobe-shi/suma-ku",
        "yahoo_pref": "28",
        "yahoo_city": "28105",
        "demand_level": 3,
        "avg_rent": 60_000,
        "comment": "住環境良好。JR山陽沿線でファミリー需要安定",
    },
    {
        "name": "兵庫県洲本市",
        "pref": "兵庫県",
        "pref_code": "28",
        "city_code": "28201",
        "suumo_ar": "050",
        "athome_path": "hyogo/sumoto-shi",
        "homes_path": "hyogo/sumoto-shi",
        "yahoo_pref": "28",
        "yahoo_city": "28201",
        "demand_level": 1,
        "avg_rent": 40_000,
        "comment": "淡路島。移住・観光需要中心。賃貸需要は薄い",
    },
    # ── 徳島県 ──
    {
        "name": "徳島県徳島市",
        "pref": "徳島県",
        "pref_code": "36",
        "city_code": "36201",
        "suumo_ar": "060",
        "athome_path": "tokushima/tokushima-shi",
        "homes_path": "tokushima/tokushima-shi",
        "yahoo_pref": "36",
        "yahoo_city": "36201",
        "demand_level": 2,
        "avg_rent": 45_000,
        "comment": "県庁所在地。単身ビジネス層の賃貸需要あり",
    },
    {
        "name": "徳島県小松島市",
        "pref": "徳島県",
        "pref_code": "36",
        "city_code": "36203",
        "suumo_ar": "060",
        "athome_path": "tokushima/komatsushima-shi",
        "homes_path": "tokushima/komatsushima-shi",
        "yahoo_pref": "36",
        "yahoo_city": "36203",
        "demand_level": 1,
        "avg_rent": 38_000,
        "comment": "工場・港湾従業員ファミリー需要。価格安め",
    },
    {
        "name": "徳島県阿南市",
        "pref": "徳島県",
        "pref_code": "36",
        "city_code": "36205",
        "suumo_ar": "060",
        "athome_path": "tokushima/anan-shi",
        "homes_path": "tokushima/anan-shi",
        "yahoo_pref": "36",
        "yahoo_city": "36205",
        "demand_level": 2,
        "avg_rent": 42_000,
        "comment": "工業地帯のファミリー賃貸需要あり",
    },
    # ── 香川県 ──
    {
        "name": "香川県高松市",
        "pref": "香川県",
        "pref_code": "37",
        "city_code": "37201",
        "suumo_ar": "060",
        "athome_path": "kagawa/takamatsu-shi",
        "homes_path": "kagawa/takamatsu-shi",
        "yahoo_pref": "37",
        "yahoo_city": "37201",
        "demand_level": 3,
        "avg_rent": 55_000,
        "comment": "四国最大都市。琴電・JRあり。賃貸需要安定",
    },
    {
        "name": "香川県坂出市",
        "pref": "香川県",
        "pref_code": "37",
        "city_code": "37202",
        "suumo_ar": "060",
        "athome_path": "kagawa/sakaide-shi",
        "homes_path": "kagawa/sakaide-shi",
        "yahoo_pref": "37",
        "yahoo_city": "37202",
        "demand_level": 2,
        "avg_rent": 45_000,
        "comment": "工業・港湾地帯。ファミリー層の実需あり",
    },
    {
        "name": "香川県丸亀市",
        "pref": "香川県",
        "pref_code": "37",
        "city_code": "37205",
        "suumo_ar": "060",
        "athome_path": "kagawa/marugame-shi",
        "homes_path": "kagawa/marugame-shi",
        "yahoo_pref": "37",
        "yahoo_city": "37205",
        "demand_level": 2,
        "avg_rent": 48_000,
        "comment": "地方中核市。製造業従業員の賃貸需要",
    },
]

# ── エリア名 → 設定のマップ（高速参照用）──
AREA_MAP = {a["name"]: a for a in AREAS}

# ──────────────────────────────────────────────
# 検索条件
# ──────────────────────────────────────────────
CRITERIA = {
    "max_price_yen": 5_000_000,       # 500万円以下
    "min_rooms": 2,                    # 2DK以上（部屋数）
    "min_layout_type": "DK",          # DK or LDK
    "parking_required": True,         # 駐車場あり（または造成可能）
    "exclude_rebuild_prohibited": True,  # 再建築不可を除外
    "sewage_required": True,           # 下水道接続済（不明は通過）
}

# ──────────────────────────────────────────────
# 賃貸需要ヒートマップ（LIFULL HOME'S 準拠）
# ──────────────────────────────────────────────
DEMAND_LABELS = {
    1: {"emoji": "🔵", "text": "低",   "color_name": "青"},
    2: {"emoji": "🟡", "text": "中",   "color_name": "黄"},
    3: {"emoji": "🟠", "text": "中高", "color_name": "橙"},
    4: {"emoji": "🔴", "text": "高",   "color_name": "赤"},
}

# gspread 用 RGB（0.0〜1.0）
DEMAND_CELL_COLORS = {
    1: {"red": 0.68, "green": 0.85, "blue": 0.90},   # 青
    2: {"red": 1.00, "green": 0.95, "blue": 0.40},   # 黄
    3: {"red": 1.00, "green": 0.65, "blue": 0.00},   # 橙
    4: {"red": 1.00, "green": 0.36, "blue": 0.25},   # 赤
}

# ──────────────────────────────────────────────
# スプレッドシート列定義（順番 = 表示順）
# ──────────────────────────────────────────────
SHEET_COLUMNS = [
    "直リンク",          # A - タップ一発で物件ページへ
    "スコア/100",        # B - 投資総合評価
    "賃貸需要",          # C - ヒートマップ色
    "エリア",            # D
    "価格（万円）",      # E
    "間取り",            # F
    "おすすめ理由",      # G
    "築年数",            # H
    "土地㎡",            # I
    "建物㎡",            # J
    "駐車場",            # K
    "再建築",            # L
    "下水道",            # M
    "掲載サイト",        # N
    "取得日時",          # O
    "物件名",            # P
    "所在地詳細",        # Q
]

SPREADSHEET_TITLE = "ぼろ戸建て投資物件リスト"

# ──────────────────────────────────────────────
# 間取りランク（スコア計算用）
# ──────────────────────────────────────────────
LAYOUT_RANK = {
    "2DK": 1, "2LDK": 2, "2SLDK": 2,
    "3K": 2, "3DK": 3, "3LDK": 4, "3SLDK": 4,
    "4K": 4, "4DK": 5, "4LDK": 6, "4SLDK": 6,
    "5K": 6, "5DK": 7, "5LDK": 8,
}
