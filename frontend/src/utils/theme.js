export function applyTelegramTheme(tg) {
  if (!tg?.themeParams) {
    return;
  }

  const root = document.documentElement;
  const theme = tg.themeParams;

  if (theme.bg_color) {
    root.style.setProperty("--bg", theme.bg_color);
  }

  if (theme.secondary_bg_color) {
    root.style.setProperty("--card", theme.secondary_bg_color);
  }

  if (theme.text_color) {
    root.style.setProperty("--text", theme.text_color);
  }

  if (theme.hint_color) {
    root.style.setProperty("--muted", theme.hint_color);
  }

  if (theme.button_color) {
    root.style.setProperty("--primary", theme.button_color);
  }

  if (theme.button_text_color) {
    root.style.setProperty("--button-text", theme.button_text_color);
  }
}