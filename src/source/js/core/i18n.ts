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
  title: string;
  searchPlaceholder: string;
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
  title: '观星地点查找器',
  searchPlaceholder: '搜索地点...',
  lightPollutionInfo: '光污染信息',
  coordinates: '坐标',
  bortleClass: '波特尔等级',
  lightPollutionLevel: '光污染程度',
  observationSuitability: '观测适宜性',
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
  title: 'Stargazing Place Finder',
  searchPlaceholder: 'Search location...',
  lightPollutionInfo: 'Light Pollution Info',
  coordinates: 'Coordinates',
  bortleClass: 'Bortle Class',
  lightPollutionLevel: 'Light Pollution Level',
  observationSuitability: 'Observation Suitability',
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
