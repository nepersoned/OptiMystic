import { create } from 'zustand'
import { translations, type Lang, type TranslationKey } from '@/i18n'

interface LangStore {
  lang: Lang
  t: (key: TranslationKey) => string
  toggleLang: () => void
}

const stored = (localStorage.getItem('om_lang') as Lang) || 'en'

export const useLangStore = create<LangStore>((set, get) => ({
  lang: stored,
  t: (key) => translations[stored][key],
  toggleLang: () => {
    const next: Lang = get().lang === 'en' ? 'kr' : 'en'
    localStorage.setItem('om_lang', next)
    set({ lang: next, t: (key) => translations[next][key] })
  },
}))
