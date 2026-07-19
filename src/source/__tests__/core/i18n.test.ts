import { describe, it, expect, beforeEach } from 'vitest';
import { setCurrentLanguage } from '@/state';
import { getText, toggleLanguage, detectUserLanguage, i18nConfig } from '@/core/i18n';

describe('getText', () => {
  beforeEach(() => {
    setCurrentLanguage('zh');
  });

  it('returns Chinese text for top-level keys', () => {
    expect(getText('title')).toBe('观星地点查找器');
    expect(getText('searchPlaceholder')).toBe('搜索地点...');
  });

  it('returns English text after switching language', () => {
    toggleLanguage(); // zh → en
    expect(getText('title')).toBe('Stargazing Place Finder');
  });

  it('resolves dot-separated nested keys', () => {
    expect(getText('bortleDescriptions.1')).toBe('1级 - 极佳暗空');
    expect(getText('suitabilityLevels.excellent')).toBe('极佳');
    expect(getText('tips.9')).toEqual([
      '极严重光污染',
      '几乎无法观星',
      '完全不适合观星',
    ]);
  });

  it('returns the key itself for missing translations', () => {
    expect(getText('nonexistent.key')).toBe('nonexistent.key');
    expect(getText('title.subtitle')).toBe('title.subtitle');
  });

  it('toggles between zh and en', () => {
    expect(getText('loadingData')).toBe('正在加载数据...');
    toggleLanguage();
    expect(getText('loadingData')).toBe('Loading data...');
    toggleLanguage();
    expect(getText('loadingData')).toBe('正在加载数据...');
  });
});

describe('i18nConfig', () => {
  it('has both zh and en tables', () => {
    expect(i18nConfig.zh).toBeDefined();
    expect(i18nConfig.en).toBeDefined();
  });

  it('zh and en have the same top-level keys', () => {
    const zhKeys = Object.keys(i18nConfig.zh!).sort();
    const enKeys = Object.keys(i18nConfig.en!).sort();
    expect(zhKeys).toEqual(enKeys);
  });

  it('bortleDescriptions have all 9 classes in both languages', () => {
    for (let i = 1; i <= 9; i++) {
      expect(i18nConfig.zh!.bortleDescriptions[i]).toBeTruthy();
      expect(i18nConfig.en!.bortleDescriptions[i]).toBeTruthy();
    }
  });
});
