import { applyTelegramTheme } from "./theme";

export function initTelegram() {
  const tg = window.Telegram?.WebApp;

  if (!tg) {
    return null;
  }

  tg.ready();
  tg.expand();

  applyTelegramTheme(tg);

  return tg;
}