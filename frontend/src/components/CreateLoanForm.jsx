import { useState } from "react";

import { getMyInviteLink } from "../api/users";
import { runTelegramInviteFlow } from "../utils/telegramInvite";
import InviteUserButton from "./InviteUserButton";

function formatUserName(user) {
  const nameParts = [
    user.first_name,
    user.last_name,
  ].filter(Boolean);

  const fullName = nameParts.join(" ");

  if (user.username) {
    return `${fullName || "Пользователь"} (@${user.username})`;
  }

  return fullName || `Пользователь #${user.id}`;
}

function CreateLoanForm({
  lenders = [],
  onCreate,
  onInviteSent,
}) {
  const [lenderId, setLenderId] = useState("");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("RUB");
  const [description, setDescription] = useState("");
  const [dueDate, setDueDate] = useState("");

  const [loading, setLoading] = useState(false);
  const [inviteLoading, setInviteLoading] = useState(false);
  const [error, setError] = useState("");
  const [infoMessage, setInfoMessage] = useState("");

  const hasAvailableLenders = lenders.length > 0;

  function getSelectedLender(lenderIdValue) {
    return lenders.find((user) => Number(user.id) === lenderIdValue);
  }

  async function handleInviteNewLender() {
    try {
      setInviteLoading(true);
      setError("");
      setInfoMessage("");

      await runTelegramInviteFlow(getMyInviteLink);

      if (onInviteSent) {
        await onInviteSent();
      }

      setInfoMessage(
        "Приглашение отправлено. После входа пользователя список кредиторов обновится автоматически при возврате в приложение."
      );
    } catch (currentError) {
      console.error(currentError);

      setError(
        "Не удалось создать ссылку приглашения"
      );
    } finally {
      setInviteLoading(false);
      setLenderId("");
    }
  }

  function handleLenderChange(e) {
    setError("");
    setInfoMessage("");
    setLenderId(e.target.value);
  }

  async function handleSubmit(e) {
    e.preventDefault();

    setError("");
    setInfoMessage("");

    const lenderIdValue = Number(lenderId);
    const amountValue = Number(amount);
    const selectedLender = getSelectedLender(lenderIdValue);

    if (!selectedLender) {
      setError(
        "Выберите кредитора из списка доступных пользователей"
      );
      return;
    }

    if (!amountValue || amountValue <= 0) {
      setError(
        "Сумма должна быть больше 0"
      );
      return;
    }

    try {
      setLoading(true);

      const payload = {
        lender_id: lenderIdValue,
        amount: amountValue,
        currency,
        description: description.trim() || null,
        due_date: dueDate ? `${dueDate}T00:00:00` : null,
      };

      await onCreate(payload);

      setLenderId("");
      setAmount("");
      setCurrency("RUB");
      setDescription("");
      setDueDate("");
    } catch (err) {
      console.error(err);

      setError(
        err.response?.data?.detail ||
          "Не удалось запросить займ"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card create-loan-card">
      <div className="form-header">
        <h2>
          Запросить займ
        </h2>

        <p>
          Выберите кредитора из вашей Telegram-сети, укажите сумму и описание заявки.
        </p>
      </div>

      {!hasAvailableLenders && (
        <div className="form-error">
          <p>
            <strong>
              У вас пока нет доступных кредиторов.
            </strong>
          </p>

          <p>
            Пригласите человека в приложение. После входа он появится в этом списке, и вы сможете запросить у него займ.
          </p>

          <div style={{ marginTop: "12px" }}>
            <InviteUserButton
              onInviteSent={onInviteSent}
            />
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <label className="form-field">
          <span>Кредитор</span>

          <select
            value={lenderId}
            onChange={handleLenderChange}
            disabled={loading || inviteLoading || !hasAvailableLenders}
          >
            <option value="">
              Выберите кредитора
            </option>

            {lenders.map((user) => (
              <option
                key={user.id}
                value={user.id}
              >
                {formatUserName(user)}
              </option>
            ))}
          </select>
        </label>

        {hasAvailableLenders && (
          <button
            type="button"
            className="secondary-button full-width"
            onClick={handleInviteNewLender}
            disabled={loading || inviteLoading}
          >
            {inviteLoading
              ? "Создаём ссылку..."
              : "+ Пригласить нового кредитора"}
          </button>
        )}

        <label className="form-field">
          <span>Сумма займа</span>

          <input
            type="number"
            placeholder="Например: 5000"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            disabled={loading || inviteLoading || !hasAvailableLenders}
          />
        </label>

        <label className="form-field">
          <span>Валюта</span>

          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            disabled={loading || inviteLoading || !hasAvailableLenders}
          >
            <option value="RUB">RUB</option>
          </select>
        </label>

        <label className="form-field">
          <span>Срок возврата</span>

          <input
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
            disabled={loading || inviteLoading || !hasAvailableLenders}
          />
        </label>

        <label className="form-field">
          <span>Описание</span>

          <input
            type="text"
            placeholder="Например: до пятницы"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={loading || inviteLoading || !hasAvailableLenders}
          />
        </label>

        {infoMessage && (
          <p className="form-success">
            {infoMessage}
          </p>
        )}

        {error && (
          <p className="form-error">
            {error}
          </p>
        )}

        <button
          type="submit"
          className="full-width create-loan-button"
          disabled={loading || inviteLoading || !hasAvailableLenders}
        >
          {loading ? "Отправка..." : "Запросить займ"}
        </button>
      </form>
    </div>
  );
}

export default CreateLoanForm;