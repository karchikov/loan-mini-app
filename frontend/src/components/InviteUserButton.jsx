import { useState } from "react";

import { getMyInviteLink } from "../api/users";

function InviteUserButton() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function openTelegramShare(inviteLink) {
    const shareUrl = new URL("https://t.me/share/url");

    shareUrl.searchParams.set(
      "url",
      inviteLink
    );

    shareUrl.searchParams.set(
      "text",
      "Присоединяйся ко мне в LoanMiniApp"
    );

    const tg = window.Telegram?.WebApp;

    if (tg?.openTelegramLink) {
      tg.openTelegramLink(
        shareUrl.toString()
      );

      return;
    }

    if (tg?.openLink) {
      tg.openLink(
        shareUrl.toString()
      );

      return;
    }

    window.location.href = shareUrl.toString();
  }

  async function handleInvite() {
    try {
      setLoading(true);
      setError("");

      const invite = await getMyInviteLink();

      openTelegramShare(
        invite.invite_link
      );
    } catch (currentError) {
      console.error(currentError);

      setError(
        "Не удалось создать ссылку приглашения"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="invite-user-card">
      <div>
        <h2 className="section-title">
          Пригласить пользователя
        </h2>

        <p className="section-description">
          Отправьте другу персональную ссылку в Telegram.
        </p>
      </div>

      <button
        className="primary-button"
        type="button"
        onClick={handleInvite}
        disabled={loading}
      >
        {loading
          ? "Создаём ссылку..."
          : "Пригласить пользователя"}
      </button>

      {error && (
        <div className="form-error">
          {error}
        </div>
      )}
    </div>
  );
}

export default InviteUserButton;