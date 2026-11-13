// =============================================================================
// i18n — multi-language configuration and text lookup
// =============================================================================

import { currentLanguage, setCurrentLanguage } from '../state';
import type { Language } from '../types/i18n';

// ---------------------------------------------------------------------------
// Language detection
// ---------------------------------------------------------------------------

export function detectUserLanguage(): Language {
  const navLang: string =
    (navigator as any).language ||
    (navigator as any).userLanguage ||
    (navigator as any).browserLanguage ||
    'zh';
  if (navLang.toLowerCase().startsWith('en')) return 'en';
  if (navLang.toLowerCase().startsWith('zh')) return 'zh';
  return 'zh';
}

// ---------------------------------------------------------------------------
// Translation tables
// ---------------------------------------------------------------------------

interface TranslationTables {
  ui: Record<string, string>;
  title: string;
  searchPlaceholder: string;
  skySearchPlaceholder: string;
  skySearchLabel: string;
  locationSearchLabel: string;
  skySearching: string;
  skyLocated: string;
  skyNotFound: string;
  skyResolverUnavailable: string;
  skySearchTimeout: string;
  skySearchFailed: string;
  lightPollutionInfo: string;
  coordinates: string;
  bortleClass: string;
  lightPollutionLevel: string;
  observationSuitability: string;
  darkSkyStats: string;
  totalDarkSkyArea: string;
  darkSkyPercentage: string;
  bortleDistribution: string;
  legend: string;
  observationTips: string;
  loadingData: string;
  languageToggle: string;
  bortleDescriptions: Record<number, string>;
  suitabilityLevels: Record<string, string>;
  tips: Record<number, string[]>;
  shootHere: string;
}

const zh: TranslationTables = {
  ui: {
    "places": "找观测地",
    "planning": "拍摄规划",
    "areaTitle": "找观测地",
    "areaIntro": "先框选区域，再按交通方式寻找地点。",
    "drawArea": "在地图框选",
    "cancelDraw": "取消框选",
    "noSelection": "尚未选择区域",
    "selected": "区域已选好，可分析或重新框选。",
    "advanced": "高级设置",
    "drawPrompt": "点击“在地图框选”开始选择区域",
    "dragPrompt": "在地图上拖拽绘制区域，按 Esc 取消。",
    "editObservation": "修改地点与时间",
    "observationPlace": "观测地点",
    "latitude": "纬度",
    "longitude": "经度",
    "observationTime": "观测时间",
    "timezone": "时区（IANA）",
    "useMapCenter": "使用地图中心",
    "useNow": "使用当前时间",
    "equipmentDetails": "设备参数与排序",
    "layerOptions": "图层说明",
    "opacity": "光污染覆盖透明度",
    "pollutionNote": "VIIRS DNB 2025 · 光污染模型估计；不代表今晚天气或实地通行条件。",
    "invalidObservation": "请检查地点、时间与设备参数，填写有效值后重试。",
    "invalidTimezone": "请输入有效时区，例如 Asia/Shanghai 或 UTC。",
    "estimated": "估计",
    "accessibilityDescription": "交互式光污染地图，可选择区域寻找地点或进入拍摄规划。",
    "maxLocations": "最多返回地点数",
    "transport": "交通方式",
    "drive": "驾车",
    "walk": "步行",
    "bike": "骑行",
    "includePollution": "包含光污染分析",
    "includeRoads": "包含道路连通性",
    "analyze": "分析观星地点",
    "clear": "清除选区与结果",
    "cancelWait": "取消等待",
    "preset": "设备预设",
    "custom": "自定义",
    "focalLength": "焦距 (mm)",
    "sensorWidth": "传感器宽 (mm)",
    "sensorHeight": "传感器高 (mm)",
    "cameraType": "相机类型（用于滤镜建议）",
    "cameraUnknown": "未指定",
    "cameraColor": "彩色相机",
    "cameraMono": "单色相机",
    "sort": "目标排序",
    "sortTime": "可拍时长优先",
    "sortUrgency": "即将结束的窗口优先",
    "sortFov": "画幅适配优先",
    "sortLegacy": "参考分（旧算法）",
    "fov": "视场 (FOV)",
    "rotation": "相机旋转",
    "showFrame": "显示画幅框",
    "targets": "推荐拍摄目标",
    "plan": "拍摄计划",
    "match": "匹配拍摄目标",
    "matching": "匹配中…",
    "loadingTargets": "正在分析拍摄目标…",
    "queryTime": "观测时间",
    "rankNote": "按所选排序方式展示；可拍时段未计天气及地形遮挡。",
    "methodTitle": "时段与滤镜建议的依据",
    "methodNote": "时段按目标高度至少 25°、太阳低于 −18°及月距筛选，15 分钟采样；未计天气、地形遮挡和设备开销。SHO 即 SII / Hα / OIII，仅依据目录类型，不代表已测得各发射线强度。拍摄计划独立调度，列表排序不是执行顺序。",
    "layerDark": "1 暗空",
    "layerBright": "9 内城",
    "skyHint": "拖动星图浏览天区 · 上方搜索天体 · 蓝色框为设备画幅",
    "fallbackNote": "未取得该点查询数据，以下为缓存或地理估计，需核实；不代表今晚天气或通行条件。"
},
  title: '观星地点查找器',
  searchPlaceholder: '搜索地点，如上海、安吉（回车确认）',
  skySearchPlaceholder: '搜索天体（如 M31、M42、NGC 7000）...',
  skySearchLabel: '搜索天体',
  locationSearchLabel: '搜索地点',
  skySearching: '正在搜索天体…',
  skyLocated: '已定位：',
  skyNotFound: '未找到该天体，请检查名称或编号',
  skyResolverUnavailable: '天体名称服务暂不可用，可重试或使用 M、NGC、IC 编号',
  skySearchTimeout: '天体搜索超时，请重试或使用 M、NGC、IC 编号',
  skySearchFailed: '天体搜索失败，请重试',
  lightPollutionInfo: '光污染信息',
  coordinates: '坐标',
  bortleClass: '波特尔等级',
  lightPollutionLevel: '光污染程度',
  observationSuitability: '仅光污染条件',
  darkSkyStats: '暗空区域统计',
  totalDarkSkyArea: '暗空区域总面积',
  darkSkyPercentage: '暗空区域占比',
  bortleDistribution: '波特尔等级分布',
  legend: '图例说明',
  observationTips: '观测建议',
  loadingData: '正在加载数据...',
  languageToggle: '中/EN',
  shootHere: '在此拍摄',
  bortleDescriptions: {
    1: '1级 - 极佳暗空', 2: '2级 - 典型暗空', 3: '3级 - 乡村天空',
    4: '4级 - 乡村/郊区过渡', 5: '5级 - 郊区天空', 6: '6级 - 明亮郊区',
    7: '7级 - 郊区/城市过渡', 8: '8级 - 城市天空', 9: '9级 - 内城天空',
  },
  suitabilityLevels: {
    excellent: '极佳', good: '良好', fair: '一般', poor: '较差', verypoor: '很差',
  },
  tips: {
    1: ['银河清晰可见', '可观测暗弱天体', '最佳观星地点'],
    2: ['银河可见', '适合深空观测', '优秀观星地点'],
    3: ['银河部分可见', '适合行星观测', '良好观星地点'],
    4: ['银河微弱可见', '适合明亮天体', '一般观星地点'],
    5: ['银河难以看见', '仅适合行星月亮', '观星条件一般'],
    6: ['银河不可见', '仅适合明亮天体', '观星条件较差'],
    7: ['天空明亮', '观星条件差', '不推荐观星'],
    8: ['严重光污染', '观星条件很差', '不适合观星'],
    9: ['极严重光污染', '几乎无法观星', '完全不适合观星'],
  },
};

const en: TranslationTables = {
  ui: {
    "places": "Find a place",
    "planning": "Imaging planner",
    "areaTitle": "Find a place",
    "areaIntro": "Select an area, then find places for your travel mode.",
    "drawArea": "Select area on map",
    "cancelDraw": "Cancel selection",
    "noSelection": "No area selected",
    "selected": "Area selected. Analyze or select again.",
    "advanced": "Advanced settings",
    "drawPrompt": "Choose “Select area on map” to begin.",
    "dragPrompt": "Drag on the map to select an area. Esc cancels.",
    "editObservation": "Edit place and time",
    "observationPlace": "Observer",
    "latitude": "Latitude",
    "longitude": "Longitude",
    "observationTime": "Observation time",
    "timezone": "Timezone (IANA)",
    "useMapCenter": "Use map center",
    "useNow": "Use current time",
    "equipmentDetails": "Equipment and sorting",
    "layerOptions": "Layer details",
    "opacity": "Light-pollution opacity",
    "pollutionNote": "VIIRS DNB 2025 · Model estimates only; weather and site access are not assessed.",
    "invalidObservation": "Check place, time and equipment values before retrying.",
    "invalidTimezone": "Enter a valid timezone, such as Asia/Shanghai or UTC.",
    "estimated": "estimate",
    "accessibilityDescription": "Interactive light-pollution map. Select an area to find places or open the imaging planner.",
    "maxLocations": "Maximum places",
    "transport": "Travel mode",
    "drive": "Driving",
    "walk": "Walking",
    "bike": "Cycling",
    "includePollution": "Include light-pollution analysis",
    "includeRoads": "Include road connectivity",
    "analyze": "Analyze places",
    "clear": "Clear area and results",
    "cancelWait": "Stop waiting",
    "preset": "Equipment preset",
    "custom": "Custom",
    "focalLength": "Focal length (mm)",
    "sensorWidth": "Sensor width (mm)",
    "sensorHeight": "Sensor height (mm)",
    "cameraType": "Camera type (filter advice)",
    "cameraUnknown": "Unspecified",
    "cameraColor": "Color camera",
    "cameraMono": "Mono camera",
    "sort": "Target ordering",
    "sortTime": "Imaging time first",
    "sortUrgency": "Ending soon first",
    "sortFov": "Framing fit first",
    "sortLegacy": "Reference score (legacy)",
    "fov": "Field of view (FOV)",
    "rotation": "Camera rotation",
    "showFrame": "Show camera frame",
    "targets": "Suggested targets",
    "plan": "Imaging plan",
    "match": "Match targets",
    "matching": "Matching…",
    "loadingTargets": "Finding imaging targets…",
    "queryTime": "Observation time",
    "rankNote": "Uses the selected ordering; windows exclude weather and terrain.",
    "methodTitle": "Window and filter methodology",
    "methodNote": "Windows use altitude ≥25°, Sun below −18° and Moon separation, sampled every 15 minutes. Weather, terrain and equipment overhead are excluded. SHO (SII / Hα / OIII) advice uses catalog type, not measured line strength. Plans use independent scheduling.",
    "layerDark": "1 Dark sky",
    "layerBright": "9 Inner city",
    "skyHint": "Drag to explore · Search objects above · Blue frame shows the camera field",
    "fallbackNote": "Point data unavailable: cached or geographic estimates below require verification. Weather and access are not assessed."
},
  title: 'Stargazing Place Finder',
  searchPlaceholder: 'Search location...',
  skySearchPlaceholder: 'Search sky objects (e.g. M31, M42, NGC 7000)...',
  skySearchLabel: 'Search sky objects',
  locationSearchLabel: 'Search location',
  skySearching: 'Searching sky objects…',
  skyLocated: 'Located: ',
  skyNotFound: 'Object not found. Check the name or catalog ID.',
  skyResolverUnavailable: 'Name service unavailable. Retry or use an M, NGC or IC identifier.',
  skySearchTimeout: 'Search timed out. Retry or use an M, NGC or IC identifier.',
  skySearchFailed: 'Sky search failed. Please retry.',
  lightPollutionInfo: 'Light Pollution Info',
  coordinates: 'Coordinates',
  bortleClass: 'Bortle Class',
  lightPollutionLevel: 'Light Pollution Level',
  observationSuitability: 'Light-pollution conditions only',
  darkSkyStats: 'Dark Sky Statistics',
  totalDarkSkyArea: 'Total Dark Sky Area',
  darkSkyPercentage: 'Dark Sky Percentage',
  bortleDistribution: 'Bortle Class Distribution',
  legend: 'Legend',
  observationTips: 'Observation Tips',
  loadingData: 'Loading data...',
  languageToggle: 'EN/中',
  shootHere: 'Shoot Here',
  bortleDescriptions: {
    1: 'Class 1 - Excellent Dark Sky', 2: 'Class 2 - Typical Dark Sky',
    3: 'Class 3 - Rural Sky', 4: 'Class 4 - Rural/Suburban Transition',
    5: 'Class 5 - Suburban Sky', 6: 'Class 6 - Bright Suburban',
    7: 'Class 7 - Suburban/Urban Transition', 8: 'Class 8 - City Sky',
    9: 'Class 9 - Inner City Sky',
  },
  suitabilityLevels: {
    excellent: 'Excellent', good: 'Good', fair: 'Fair', poor: 'Poor', verypoor: 'Very Poor',
  },
  tips: {
    1: ['Milky Way clearly visible', 'Deep sky objects observable', 'Best stargazing location'],
    2: ['Milky Way visible', 'Good for deep sky observation', 'Excellent stargazing location'],
    3: ['Milky Way partially visible', 'Good for planetary observation', 'Good stargazing location'],
    4: ['Milky Way faintly visible', 'Suitable for bright objects', 'Fair stargazing location'],
    5: ['Milky Way hard to see', 'Only planets and moon', 'Average stargazing conditions'],
    6: ['Milky Way not visible', 'Only bright objects', 'Poor stargazing conditions'],
    7: ['Bright sky', 'Poor stargazing conditions', 'Not recommended for stargazing'],
    8: ['Severe light pollution', 'Very poor stargazing', 'Not suitable for stargazing'],
    9: ['Extreme light pollution', 'Nearly impossible to stargaze', 'Completely unsuitable for stargazing'],
  },
};

export const i18nConfig: Record<string, TranslationTables> = { zh, en };

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function getText(key: string): any {
  const table = i18nConfig[currentLanguage] as Record<string, any> | undefined;
  if (!table) return key;
  const keys = key.split('.');
  let value: any = table;
  for (const k of keys) {
    if (value == null || typeof value !== 'object') return key;
    value = value[k];
  }
  return value ?? key;
}

export function toggleLanguage(): void {
  const next: Language = currentLanguage === 'zh' ? 'en' : 'zh';
  setCurrentLanguage(next);
}
