/** Telegram Web App bilan ishlash. Oddiy brauzerda barcha funksiyalar xavfsiz "hech narsa qilmaydi". */

interface TgWebApp {
  initData: string;
  colorScheme: "light" | "dark";
  themeParams: Record<string, string | undefined>;
  platform: string;
  ready(): void;
  expand(): void;
  openLink(url: string): void;
  openTelegramLink(url: string): void;
  close(): void;
  setHeaderColor?(color: string): void;
  setBackgroundColor?(color: string): void;
  BackButton: { show(): void; hide(): void; onClick(cb: () => void): void; offClick(cb: () => void): void };
  HapticFeedback?: {
    impactOccurred(style: "light" | "medium" | "heavy"): void;
    notificationOccurred(type: "success" | "error" | "warning"): void;
  };
  onEvent(event: string, cb: () => void): void;
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TgWebApp };
  }
}

export const tg: TgWebApp | undefined =
  typeof window !== "undefined" && window.Telegram?.WebApp?.initData ? window.Telegram.WebApp : undefined;

export const isTelegram = Boolean(tg);

function hexToRgb(hex?: string): string | null {
  if (!hex) return null;
  const m = hex.replace("#", "").match(/^([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i);
  if (!m) return null;
  return `${parseInt(m[1], 16)} ${parseInt(m[2], 16)} ${parseInt(m[3], 16)}`;
}

/** Telegram mavzusi ranglarini sayt tokenlariga ulaydi. */
export function initTelegram() {
  if (!tg) return;
  tg.ready();
  tg.expand();
  const root = document.documentElement;
  root.classList.toggle("dark", tg.colorScheme === "dark");
  root.classList.add("tg");
  const p = tg.themeParams;
  const map: Record<string, string | undefined> = {
    "--bg": p.secondary_bg_color || p.bg_color,
    "--surface": p.bg_color,
    "--ink": p.text_color,
    "--muted": p.hint_color,
    "--accent": p.button_color,
    "--accent-ink": p.button_text_color,
  };
  for (const [k, hex] of Object.entries(map)) {
    const rgb = hexToRgb(hex);
    if (rgb) root.style.setProperty(k, rgb);
  }
  try {
    if (p.secondary_bg_color) tg.setHeaderColor?.(p.secondary_bg_color);
    if (p.secondary_bg_color) tg.setBackgroundColor?.(p.secondary_bg_color);
  } catch {
    /* eski Telegram versiyalari */
  }
}

export function haptic(kind: "success" | "error" | "light" = "light") {
  try {
    if (kind === "light") tg?.HapticFeedback?.impactOccurred("light");
    else tg?.HapticFeedback?.notificationOccurred(kind);
  } catch {
    /* yo'q bo'lsa e'tiborsiz */
  }
}

export function openExternal(url: string) {
  if (tg) tg.openLink(url);
  else window.open(url, "_blank", "noopener");
}
