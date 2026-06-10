import { useState } from "react";

import { getMyInviteLink } from "../api/users";

function InviteUserButton() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleInvite() {
    try {
      setLoading(true);
      setError("");

      const invite = await getMyInviteLink();

      const shareUrl = new URL("https://t.me/share/url");

      shareUrl.searchParams.set(
        "url",
        invite.invite_link
      );

      shareUrl.searchParams.set(
        "text",
        "Присоединяйся ко мне в LoanMiniApp"
      );

      window.open(
        shareUrl.toString(),
        "_blank"
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