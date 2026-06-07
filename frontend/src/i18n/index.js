import { createI18n } from 'vue-i18n'
import enUS from './locales/en-US'
import zhCN from './locales/zh-CN'
import zhTW from './locales/zh-TW'
import ja from './locales/ja'

const SUPPORTED_LOCALES = ['en-US', 'zh-CN', 'zh-TW', 'ja']

function detectLocale() {
  const saved = localStorage.getItem('webtty-locale')
  if (saved && SUPPORTED_LOCALES.includes(saved)) return saved

  const browserLang = navigator.language
  if (SUPPORTED_LOCALES.includes(browserLang)) return browserLang

  // Try matching language part only (e.g. "zh-Hans-CN" -> "zh-CN")
  const langPrefix = browserLang.split('-')[0]
  const match = SUPPORTED_LOCALES.find(l => l.startsWith(langPrefix))
  if (match) return match

  return 'en-US'
}

const i18n = createI18n({
  legacy: false,
  locale: detectLocale(),
  fallbackLocale: 'en-US',
  messages: {
    'en-US': enUS,
    'zh-CN': zhCN,
    'zh-TW': zhTW,
    'ja': ja
  }
})

export function setLocale(locale) {
  i18n.global.locale.value = locale
  localStorage.setItem('webtty-locale', locale)
  document.documentElement.setAttribute('lang', locale)
}

export function getSupportedLocales() {
  return SUPPORTED_LOCALES
}

export default i18n
