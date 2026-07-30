"""Heuristic popularity and temporal-quiet analysis."""

from __future__ import annotations

import re

from models import Location, StargazingLocation

from .models import PopularityResult

_SCENIC_KEYWORDS = (
    "viewpoint",
    "lookout",
    "observation",
    "scenic",
    "park",
    "camp",
    "glamp",
    "resort",
    "planetarium",
    "tourist",
    "观景",
    "景区",
    "公园",
    "营地",
    "打卡",
    "度假",
    "游客",
)

_NIGHT_ACTIVE_KEYWORDS = (
    "camp",
    "glamp",
    "hotel",
    "resort",
    "planetarium",
    "night",
    "星空营地",
    "露营",
    "营地",
    "酒店",
    "度假",
    "夜游",
)

_DAY_ONLY_KEYWORDS = (
    "viewpoint",
    "lookout",
    "park",
    "scenic",
    "visitor",
    "观景",
    "景区",
    "公园",
    "游客",
    "打卡",
)


def analyze_location_popularity(raw_location: Location, location: StargazingLocation) -> PopularityResult:
    """Estimate static popularity and night quietness from existing location context."""
    text = _combine_text(raw_location)
    scenic_hits = _count_keyword_hits(text, _SCENIC_KEYWORDS)
    night_hits = _count_keyword_hits(text, _NIGHT_ACTIVE_KEYWORDS)
    day_hits = _count_keyword_hits(text, _DAY_ONLY_KEYWORDS)

    static_score = 0.0
    quiet_score = 45.0
    confidence = 20.0
    popularity_signals: list[str] = []
    temporal_signals: list[str] = []

    if location.is_viewpoint():
        static_score += 18.0
        quiet_score += 8.0
        popularity_signals.append("候选点自身属于观景点类型")
        temporal_signals.append("观景点往往白天更活跃，夜间有退潮可能")
        confidence += 10.0
    elif location.is_observatory():
        static_score += 10.0
        quiet_score -= 4.0
        popularity_signals.append("候选点自身属于天文台/观测设施类型")
        temporal_signals.append("天文设施可能在夜间仍保持活动")
        confidence += 10.0
    else:
        quiet_score += 15.0
        temporal_signals.append("山顶/自然点位通常缺少持续夜间商业活动")
        confidence += 6.0

    if scenic_hits:
        static_score += min(24.0, scenic_hits * 6.0)
        popularity_signals.append(f"名称或描述命中 {scenic_hits} 个景点/观景关键词")
        confidence += min(12.0, scenic_hits * 3.0)

    if night_hits:
        static_score += min(18.0, night_hits * 5.0)
        quiet_score -= min(24.0, night_hits * 7.0)
        popularity_signals.append(f"命中 {night_hits} 个夜间活跃关键词")
        temporal_signals.append("周边语义显示夜间活动可能持续")
        confidence += min(14.0, night_hits * 4.0)

    if day_hits:
        quiet_score += min(16.0, day_hits * 4.0)
        temporal_signals.append(f"命中 {day_hits} 个偏白天场景关键词")
        confidence += min(10.0, day_hits * 2.0)

    if location.distance_to_nearest_town is not None:
        if location.distance_to_nearest_town < 10:
            static_score += 20.0
            quiet_score -= 14.0
            popularity_signals.append("距离最近城镇较近")
            temporal_signals.append("靠近城镇意味着夜间残余人流概率更高")
        elif location.distance_to_nearest_town < 25:
            static_score += 12.0
            quiet_score -= 6.0
            popularity_signals.append("与城镇距离中等")
        elif location.distance_to_nearest_town >= 50:
            quiet_score += 18.0
            temporal_signals.append("远离城镇，夜间退潮概率更高")
        elif location.distance_to_nearest_town >= 25:
            quiet_score += 10.0
        confidence += 14.0

    if location.nearby_town_count == 0:
        quiet_score += 12.0
        temporal_signals.append("20km 内几乎没有额外城镇信号")
        confidence += 8.0
    elif location.nearby_town_count == 1:
        static_score += 4.0
        quiet_score += 4.0
        popularity_signals.append("周边存在少量城镇信号")
        confidence += 8.0
    else:
        static_score += min(20.0, float(location.nearby_town_count) * 4.0)
        quiet_score -= min(18.0, float(location.nearby_town_count) * 3.0)
        popularity_signals.append(f"20km 内检测到 {location.nearby_town_count} 个额外城镇信号")
        temporal_signals.append("多城镇环境往往伴随更连续的夜间活动")
        confidence += 10.0

    if location.distance_to_road_km is not None:
        if location.distance_to_road_km <= 0.05:
            static_score += 12.0
            quiet_score -= 10.0
            popularity_signals.append("距道路极近，可达性很强")
        elif location.distance_to_road_km <= 0.2:
            static_score += 8.0
            quiet_score -= 5.0
            popularity_signals.append("距道路较近，临时到访成本较低")
        elif location.distance_to_road_km >= 1.0:
            quiet_score += 8.0
            temporal_signals.append("距道路较远，夜间停留门槛更高")
        confidence += 12.0
    elif location.road_accessible is False:
        quiet_score += 8.0
        temporal_signals.append("道路不可直达，夜间持续热闹概率较低")
        confidence += 10.0

    nearby_popular_poi_count = min(
        99,
        int(location.nearby_town_count + scenic_hits + night_hits + (1 if location.is_viewpoint() else 0)),
    )
    nearby_night_active_poi_count = min(99, int(night_hits + (1 if location.is_observatory() else 0)))
    nearby_day_only_poi_count = min(
        99,
        int(day_hits + (1 if location.is_viewpoint() and night_hits == 0 else 0)),
    )

    static_score = _clamp(static_score)
    quiet_score = _clamp(quiet_score)
    confidence = _clamp(confidence)

    notes = _build_notes(
        static_score=static_score,
        quiet_score=quiet_score,
        popularity_signals=popularity_signals,
        temporal_signals=temporal_signals,
    )

    return PopularityResult(
        static_popularity_risk_score=round(static_score, 1),
        night_quiet_likelihood_score=round(quiet_score, 1),
        temporal_popularity_confidence=round(confidence, 1),
        nearby_popular_poi_count=nearby_popular_poi_count,
        nearby_night_active_poi_count=nearby_night_active_poi_count,
        nearby_day_only_poi_count=nearby_day_only_poi_count,
        popularity_signals=popularity_signals,
        temporal_popularity_signals=temporal_signals,
        popularity_notes=notes,
    )


def _combine_text(raw_location: Location) -> str:
    """Combine stable text attributes into a keyword-searchable blob."""
    raw_parts = [
        raw_location.name,
        raw_location.description,
        getattr(raw_location, "observatory_type", ""),
        getattr(raw_location, "viewpoint_type", ""),
        getattr(raw_location, "scenic_value", ""),
    ]
    parts: list[str] = []
    for value in raw_parts:
        if value is None:
            continue
        if isinstance(value, str):
            parts.append(value)
            continue
        parts.append(str(value))
    return " ".join(parts).lower()


def _count_keyword_hits(text: str, keywords: tuple[str, ...]) -> int:
    """Count distinct keyword hits inside free text."""
    hits = 0
    for keyword in keywords:
        if re.search(re.escape(keyword.lower()), text):
            hits += 1
    return hits


def _clamp(value: float) -> float:
    """Clamp heuristic scores into the normalized [0, 100] range."""
    return max(0.0, min(100.0, value))


def _build_notes(
    static_score: float,
    quiet_score: float,
    popularity_signals: list[str],
    temporal_signals: list[str],
) -> str:
    """Build a concise human-readable popularity summary."""
    risk_label = "热门风险高" if static_score >= 60 else ("热门风险中等" if static_score >= 35 else "热门风险较低")
    quiet_label = (
        "夜间大概率退潮"
        if quiet_score >= 65
        else ("夜间可能保持一定安静度" if quiet_score >= 45 else "夜间仍可能保持活跃")
    )

    snippets = [risk_label, quiet_label]
    if popularity_signals:
        snippets.append(popularity_signals[0])
    if temporal_signals:
        snippets.append(temporal_signals[0])
    return "; ".join(snippets)
