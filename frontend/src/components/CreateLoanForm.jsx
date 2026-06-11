import { useState } from "react";

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
}) {
  const [lenderId, setLenderId] = useState("");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("RUB");
  const [description, setDescription] = useState("");
  const [dueDate, setDueDate] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const hasAvailableLenders = lenders.length > 0;

  async function handleSubmit(e) {
    e.preventDefault();

    setError("");

    const lenderIdValue = Number(lenderId);
    const amountValue = Number(amount);

    if (!lenderIdValue || lenderIdValue <= 0) {
      setError("Выберите кредитора");
      return;
    }

    if (!amountValue || amountValue <= 0) {
      setError("Сумма должна быть больше 0");
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
            Чтобы запросить займ:
          </p>

          <ol style={{ marginTop: "8px", paddingLeft: "20px" }}>
            <li>
              Пригласите пользователя через Telegram.
            </li>

            <li>
              Пользователь должен открыть приложение по вашей ссылке.
            </li>

            <li>
              После этого он автоматически появится в вашем списке кредиторов.
            </li>
          </ol>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <label className="form-field">
          <span>Кредитор</span>

          <select
            value={lenderId}
            onChange={(e) => setLenderId(e.target.value)}
            disabled={loading || !hasAvailableLenders}
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

        <label className="form-field">
          <span>Сумма займа</span>

          <input
            type="number"
            placeholder="Например: 5000"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            disabled={loading || !hasAvailableLenders}
          />
        </label>

        <label className="form-field">
          <span>Валюта</span>

          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            disabled={loading || !hasAvailableLenders}
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
            disabled={loading || !hasAvailableLenders}
          />
        </label>

        <label className="form-field">
          <span>Описание</span>

          <input
            type="text"
            placeholder="Например: до пятницы"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={loading || !hasAvailableLenders}
          />
        </label>

        {error && <p className="form-error">{error}</p>}

        <button
          type="submit"
          className="full-width create-loan-button"
          disabled={loading || !hasAvailableLenders}
        >
          {loading ? "Отправка..." : "Запросить займ"}
        </button>
      </form>
    </div>
  );
}

export default CreateLoanForm;