import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../services/api";
import { useAuth } from "./AuthContext";
import { DEFAULT_LANG, isSupportedLang, translate } from "../utils/i18n";

interface LanguageContextValue {
  language: string;
  setLanguage: (lang: string) => void;
  /** Translate a chrome key into the active language (English fallback). */
  t: (key: string, vars?: Record<string, string | number>) => string;
}

const LanguageContext = createContext<LanguageContextValue>({
  language: DEFAULT_LANG,
  setLanguage: () => {},
  t: (key) => key,
});

const STORAGE_KEY = "lcd_language";

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const { user, refreshUser } = useAuth();
  const [language, setLanguageState] = useState<string>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && isSupportedLang(saved)) return saved;
    return DEFAULT_LANG;
  });

  // Initialize from the account language once the user profile is available.
  useEffect(() => {
    if (user?.language && isSupportedLang(user.language) && user.language !== language) {
      setLanguageState(user.language);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.language]);

  const setLanguage = (lang: string) => {
    if (!isSupportedLang(lang)) return;
    setLanguageState(lang);
    localStorage.setItem(STORAGE_KEY, lang);
    // Persist to the account so the preference follows the user across devices.
    if (user) {
      api
        .put("/settings", { language: lang })
        .then(() => void refreshUser())
        .catch(() => {
          /* offline: preference still applied locally for this session */
        });
    }
  };

  const value = useMemo<LanguageContextValue>(
    () => ({
      language,
      setLanguage,
      t: (key, vars) => translate(language, key, vars),
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [language, user?.id],
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  return useContext(LanguageContext);
}
