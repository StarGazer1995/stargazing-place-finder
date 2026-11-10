"""SPF-only target explanations; no changes to the public MCP contract."""

import math
from typing import Literal

import astropy.units as u
import numpy as np
from astropy.coordinates import AltAz, EarthLocation, SkyCoord, get_body, get_sun
from astropy.time import Time
from pydantic import BaseModel, Field

CameraType = Literal["unknown", "color", "mono"]
SortMode = Literal["imaging_time", "setting_soon", "fov", "heuristic"]


class TargetDisplayOptions(BaseModel):
    # Keep the REST default for existing callers; the page explicitly requests time order.
    sort_by: SortMode = "heuristic"
    camera_type: CameraType = "unknown"
    limit: int = Field(default=20, ge=1, le=100)


class ImagingWindow(BaseModel):
    start: float
    end: float


class VisibilitySummary(BaseModel):
    total_minutes: float | None = None
    longest_minutes: float | None = None
    available_now: bool | None = None
    windows: list[ImagingWindow] = Field(default_factory=list)


class SHOAdvice(BaseModel):
    status: Literal["consider", "not_primary", "verify"]
    label: str
    reason: str
    camera_note: str
    basis: str = "catalog_type_only"
    sii_strength: None = None


def sho_advice(object_type: str | None, camera_type: CameraType) -> SHOAdvice:
    """Type-based guidance is not a measurement of the three emission lines."""
    kind = object_type.strip().lower() if isinstance(object_type, str) else ""
    if kind in {"hii", "emission nebula", "star-forming region"}:
        status, label = "consider", "SHO：可考虑，先核实 SII"
        reason = "发射星云可考虑窄带；目录类型不能证明 SII 和 OIII 足够强。"
    elif kind in {"snr", "supernova remnant", "pn", "planetary nebula"}:
        status, label = "verify", "SHO：需逐目标核实"
        reason = "可先评估 Hα/OIII；完整 SHO 还需要核实 SII，不能按类别一概推荐。"
    elif kind in {"opc", "open cluster"}:
        status, label = "verify", "SHO：先核实伴生星云"
        reason = "目录仅标为疏散星团，未区分取景是否包括伴生发射星云；纯星团主体优先宽带，SHO 需另查发射线。"
    elif kind in {"glc", "globular cluster"}:
        status, label = "not_primary", "SHO：星团主体优先宽带"
        reason = "星团主体以恒星连续光谱为主；若取景包含伴生发射星云，需另外核实。"
    elif kind in {
        "g",
        "gx",
        "gig",
        "gip",
        "gic",
        "agn",
        "syg",
        "sy1",
        "sy2",
        "lin",
        "bll",
        "sbg",
        "h2g",
        "pag",
        "ig",
        "rg",
        "emg",
        "galaxy",
        "rne",
        "reflection nebula",
    }:
        status, label = "not_primary", "SHO：不建议作为主体方案"
        reason = "主体优先宽带 RGB/LRGB；发射区可另加窄带，不等于整幅适合 SHO。"
    else:
        status, label = "verify", "SHO：资料不足，待核实"
        reason = "目录未明确给出可用的发射线信息，不能据此确认 SHO 适合程度。"
    notes = {
        "color": "彩色相机：常见 Hα/OIII 双窄带缺少独立 SII；需额外 SII 或配对双窄带采集，不能直接当作实测 SHO。",
        "mono": "单色相机：可分别采集 SII、Hα、OIII；各通道是否值得投入仍需核实。",
        "unknown": "相机类型未指定；完整 SHO 需要可分离的 SII、Hα、OIII 数据。",
    }
    return SHOAdvice(status=status, label=label, reason=reason, camera_note=notes[camera_type])


def summarize_windows(times: list[float], eligible: list[bool], now: float) -> VisibilitySummary:
    """Both endpoints must pass; do not bridge missing samples or elapsed time."""
    windows: list[ImagingWindow] = []
    for index in range(len(times) - 1):
        start, end = times[index], times[index + 1]
        if not (0 < end - start <= 901 and eligible[index] and eligible[index + 1]):
            continue
        start = max(start, now)
        if start >= end:
            continue
        if windows and windows[-1].end == start:
            windows[-1].end = end
        else:
            windows.append(ImagingWindow(start=start, end=end))
    durations = [(window.end - window.start) / 60 for window in windows]
    return VisibilitySummary(
        total_minutes=round(sum(durations), 1),
        longest_minutes=round(max(durations, default=0), 1),
        available_now=any(window.start <= now < window.end for window in windows),
        windows=windows,
    )


def explain_targets(
    targets: list[dict], moon: dict, observer: EarthLocation, now: Time, camera_type: CameraType
) -> list[dict]:
    """Batch geometry over returned samples, preserving unknown/missing evidence."""
    result = [
        {
            **target,
            "visibility": VisibilitySummary().model_dump(),
            "sho_advice": sho_advice(target.get("type", ""), camera_type).model_dump(),
        }
        for target in targets
    ]
    valid: list[int] = []
    for index, target in enumerate(result):
        curve = target.get("altitude_curve", [])
        try:
            times = [float(point["time"]) for point in curve]
            values = times + [float(point["alt"]) for point in curve] + [float(target["ra"]), float(target["dec"])]
            if len(times) < 2 or not all(math.isfinite(value) for value in values):
                continue
            if not all(0 < right - left <= 901 for left, right in zip(times, times[1:])):
                continue
            if not -90 <= float(target["dec"]) <= 90:
                continue
        except (KeyError, ValueError, TypeError):
            continue
        valid.append(index)
    illumination = moon.get("illumination")
    if (
        not valid
        or not isinstance(illumination, (int, float))
        or not math.isfinite(illumination)
        or not 0 <= illumination <= 1
    ):
        return result
    times = sorted({float(point["time"]) for index in valid for point in result[index]["altitude_curve"]})
    grid = Time(times, format="unix")
    frames = AltAz(obstime=grid, location=observer)
    dark = get_sun(grid).transform_to(frames).alt.deg <= -18
    coords = SkyCoord(
        [float(result[index]["ra"]) for index in valid] * u.deg,
        [float(result[index]["dec"]) for index in valid] * u.deg,
    )
    moon_ok = np.ones((len(valid), len(times)), dtype=bool)
    if illumination > 0.1:
        moon_positions = get_body("moon", grid, location=observer).transform_to(frames)
        for j in range(len(times)):
            if moon_positions[j].alt.deg > 0:
                moon_ok[:, j] = coords.transform_to(frames[j]).separation(moon_positions[j]).deg >= 15
    positions = {timestamp: j for j, timestamp in enumerate(times)}
    for row, index in enumerate(valid):
        curve = result[index]["altitude_curve"]
        timestamps = [float(point["time"]) for point in curve]
        eligible = [
            float(point["alt"]) >= 25 and bool(dark[positions[stamp]]) and bool(moon_ok[row, positions[stamp]])
            for point, stamp in zip(curve, timestamps)
        ]
        result[index]["visibility"] = summarize_windows(timestamps, eligible, float(now.unix)).model_dump()
    return result


def sort_targets(targets: list[dict], mode: SortMode) -> list[dict]:
    """No unknown value is replaced with a favorable estimate; sort before limiting."""

    def number(value: float | None) -> float:
        return value if value is not None and math.isfinite(value) else -math.inf

    def key(target: dict) -> tuple:
        visibility = target["visibility"]
        windows = visibility["windows"]
        total = visibility["total_minutes"]
        longest = visibility["longest_minutes"]
        if mode == "imaging_time":
            return (-number(total), -number(longest), -number(target.get("fov_fit_score")), target["name"])
        if mode == "setting_soon":
            ready = visibility["available_now"]
            return (
                0 if ready else 1 if windows else 2,
                windows[0]["end"] if ready else windows[0]["start"] if windows else math.inf,
                target["name"],
            )
        if mode == "fov":
            return (-number(target.get("fov_fit_score")), -number(total), target["name"])
        return (-number(target.get("suitability_score")), target.get("dawn_altitude", math.inf))

    # Time-based modes must not recommend a known insufficient remaining window.
    candidates = [
        target
        for target in targets
        if mode not in {"imaging_time", "setting_soon"}
        or target["visibility"]["longest_minutes"] is None
        or any(window["end"] - window["start"] >= 1800 for window in target["visibility"]["windows"])
    ]
    return sorted(candidates, key=key)
