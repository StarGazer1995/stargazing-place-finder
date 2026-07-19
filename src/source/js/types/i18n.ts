// =============================================================================
// i18n / internationalization types
// =============================================================================

/** Supported languages. */
export type Language = 'zh' | 'en';

/** Translation table (key → translated string). */
export type TranslationTable = Record<string, string>;

/** Complete i18n configuration for both languages. */
export interface I18nConfig {
  zh: TranslationTable;
  en: TranslationTable;
}

/** Bortle scale observation tips keyed by bortle class (1–9). */
export type BortleTips = Record<number, string[]>;
