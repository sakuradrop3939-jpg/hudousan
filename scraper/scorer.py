"""
物件スコアリングエンジン（100点満点）

配点:
  価格スコア       30点  ── 安いほど高得点
  賃貸需要スコア   25点  ── ヒートマップ色ベース
  物件スペック     25点  ── 築年数10+間取り8+土地面積7
  投資利回り推定   20点  ── 地域平均家賃÷価格で表面利回り算出
"""
import re
from dataclasses import dataclass

from .config import AREAS, AREA_MAP, DEMAND_LABELS, LAYOUT_RANK


@dataclass
class ScoreResult:
    total: int                # 0〜100
    price_score: int          # 0〜30
    demand_score: int         # 0〜25
    spec_score: int           # 0〜25
    yield_score: int          # 0〜20
    estimated_yield: float    # 想定表面利回り（%）
    demand_level: int         # 1〜4
    reason: str               # おすすめ理由テキスト


def score(prop, area_cfg: dict = None) -> ScoreResult:
    """
    Property オブジェクトにスコアを付ける。
    area_cfg が None の場合は area_name から自動解決。
    """
    if area_cfg is None:
        area_cfg = AREA_MAP.get(prop.area_name, AREAS[0])

    reasons = []

    # ──────────────────────────────────────────────
    # 1. 価格スコア（30点）
    # ──────────────────────────────────────────────
    pm = prop.price_man or (prop.price // 10_000)
    if pm <= 0:
        price_score = 0
    elif pm <= 50:
        price_score = 30
        reasons.append(f"価格{pm}万円と超破格")
    elif pm <= 100:
        price_score = 28
        reasons.append(f"価格{pm}万円と極めて安価")
    elif pm <= 150:
        price_score = 26
        reasons.append(f"価格{pm}万円と非常に安価")
    elif pm <= 200:
        price_score = 23
        reasons.append(f"価格{pm}万円と安価")
    elif pm <= 300:
        price_score = 19
        reasons.append(f"価格{pm}万円")
    elif pm <= 400:
        price_score = 14
        reasons.append(f"価格{pm}万円")
    else:
        price_score = 9
        reasons.append(f"価格{pm}万円")

    # ──────────────────────────────────────────────
    # 2. 賃貸需要スコア（25点）ヒートマップ準拠
    # ──────────────────────────────────────────────
    demand_level = area_cfg.get("demand_level", 2)
    demand_score_map = {1: 6, 2: 13, 3: 20, 4: 25}
    demand_score = demand_score_map.get(demand_level, 13)

    dl = DEMAND_LABELS.get(demand_level, DEMAND_LABELS[2])
    area_comment = area_cfg.get("comment", "")
    reasons.append(
        f"{area_cfg['name']}の賃貸需要は{dl['emoji']}{dl['text']}（{area_comment}）"
    )

    # ──────────────────────────────────────────────
    # 3. 物件スペックスコア（25点）
    #    築年数 10点 + 間取り 8点 + 土地面積 7点
    # ──────────────────────────────────────────────
    # 築年数（10点）
    age = prop.building_age or 40
    if age <= 5:
        age_score = 10
    elif age <= 10:
        age_score = 9
    elif age <= 15:
        age_score = 8
    elif age <= 20:
        age_score = 7
    elif age <= 25:
        age_score = 5
    elif age <= 30:
        age_score = 4
    elif age <= 40:
        age_score = 3
    else:
        age_score = 1

    if age > 0:
        reasons.append(f"築{age}年")

    # 間取り（8点）
    layout_upper = prop.layout.upper() if prop.layout else ""
    layout_pts = 2  # デフォルト
    for key, pts in LAYOUT_RANK.items():
        if key in layout_upper:
            layout_pts = pts
            break
    layout_score = min(layout_pts, 8)

    if prop.layout:
        reasons.append(f"間取り{prop.layout}")

    # 土地面積（7点）
    land = prop.land_area or 0
    if land >= 200:
        land_score = 7
    elif land >= 150:
        land_score = 6
    elif land >= 100:
        land_score = 5
    elif land >= 80:
        land_score = 4
    elif land >= 60:
        land_score = 3
    elif land >= 40:
        land_score = 2
    else:
        land_score = 1

    if land > 0:
        reasons.append(f"土地{land:.0f}㎡")

    spec_score = age_score + layout_score + land_score

    # ──────────────────────────────────────────────
    # 4. 投資利回り推定スコア（20点）
    # ──────────────────────────────────────────────
    avg_rent = area_cfg.get("avg_rent", 50_000)
    price_yen = prop.price or (pm * 10_000) or 1
    annual_rent = avg_rent * 12
    estimated_yield = (annual_rent / price_yen) * 100 if price_yen > 0 else 0

    if estimated_yield >= 15:
        yield_score = 20
    elif estimated_yield >= 12:
        yield_score = 18
    elif estimated_yield >= 10:
        yield_score = 16
    elif estimated_yield >= 8:
        yield_score = 13
    elif estimated_yield >= 6:
        yield_score = 10
    elif estimated_yield >= 4:
        yield_score = 6
    else:
        yield_score = 2

    reasons.append(
        f"想定表面利回り{estimated_yield:.1f}%"
        f"（月額想定賃料{avg_rent // 10_000}万円）"
    )

    # ── 加点ボーナス ──
    bonus = 0
    if prop.parking is True:
        bonus += 1
        reasons.append("駐車場あり")
    if prop.rebuild_ok is True:
        bonus += 1
    if prop.sewage is True:
        bonus += 1
        reasons.append("公共下水接続済")

    total = min(100, price_score + demand_score + spec_score + yield_score + bonus)
    reason_text = "。".join(reasons) + "。"

    return ScoreResult(
        total=total,
        price_score=price_score,
        demand_score=demand_score,
        spec_score=spec_score,
        yield_score=yield_score,
        estimated_yield=estimated_yield,
        demand_level=demand_level,
        reason=reason_text,
    )


def passes_criteria(prop, criteria: dict) -> tuple[bool, str]:
    """
    条件チェック。True なら通過。False の場合は除外理由も返す。
    ※ 情報不明（パース失敗）の場合は除外しない。明示的にNGな場合のみ除外。
    """
    # 価格（0=パース失敗は通過。明示的に500万超のみ除外）
    if prop.price > 0 and prop.price > criteria["max_price_yen"]:
        return False, f"価格{prop.price_man}万円超過"

    # 間取り（空=パース失敗は通過。明示的に1K等の場合のみ除外）
    if prop.layout:
        layout = prop.layout.upper()
        room_count = _extract_room_count(layout)
        layout_type = _extract_layout_type(layout)
        if room_count > 0 and room_count < criteria["min_rooms"]:
            return False, f"間取り不足({prop.layout})"
        if layout_type and layout_type not in ("DK", "LDK", "LK"):
            return False, f"間取り種別不適({prop.layout})"

    # 再建築不可（明示的に不可の場合のみ除外）
    if criteria["exclude_rebuild_prohibited"] and prop.rebuild_ok is False:
        return False, "再建築不可"

    # 下水道（明示的に未接続の場合のみ除外。不明は通過）
    if criteria["sewage_required"] and prop.sewage is False:
        return False, "下水道未接続"

    # 駐車場（明示的になしの場合のみ除外。不明は通過）
    if criteria["parking_required"] and prop.parking is False:
        return False, "駐車場なし"

    return True, ""


def _extract_room_count(layout: str) -> int:
    m = re.match(r'(\d+)', layout)
    return int(m.group(1)) if m else 0


def _extract_layout_type(layout: str) -> str:
    m = re.search(r'(LDK|DK|LK|K)', layout)
    return m.group(1) if m else ""
