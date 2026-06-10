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
  users,
  currentUser,
  isAdmin,
  onCreate,
}) {
  const [lenderId, setLenderId] = useState("");
  const [borrowerId, setBorrowerId] = useState("");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const selectedLenderId = lenderId
    ? Number(lenderId)
    : currentUser.id;

  const borrowerOptions = users.filter((user) => {
    return user.id !== selectedLenderId;
  });

  const lenderOptions = users.filter((user) => {
    if (borrowerId) {
      return user.id !== Number(borrowerId);
    }

    return true;
  });

  async function handleSubmit(e) {
    e.preventDefault();

    setError("");

    const borrowerIdValue = Number(borrowerId);
    const lenderIdValue = lenderId ? Number(lenderId) : null;
    const amountValue = Number(amount);

    if (!borrowerIdValue || borrowerIdValue <= 0) {
      setError("Выберите заемщика");
      return;
    }

    if (isAdmin && lenderIdValue === borrowerIdValue) {
      setError("Кредитор и заемщик должны быть разными пользователями");
      return;
    }

    if (!isAdmin && borrowerIdValue === currentUser.id) {
      setError("Нельзя создать займ самому себе");
      return;
    }

    if (!amountValue || amountValue <= 0) {
      setError("Сумма должна быть больше 0");
      return;
    }

    try {
      setLoading(true);

      const payload = {
        borrower_id: borrowerIdValue,
        amount: amountValue,
        description: description.trim() || null,
      };

      if (isAdmin && lenderIdValue) {
        payload.lender_id = lenderIdValue;
      }

      await onCreate(payload);

      setLenderId("");
      setBorrowerId("");
      setAmount("");
      setDescription("");
    } catch (err) {
      console.error(err);

      setError(
        err.response?.data?.detail ||
          "Не удалось создать займ"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card create-loan-card">
      <div className="form-header">
        <h2>
          {isAdmin ? "Создать займ" : "Создать займ"}
        </h2>

        <p>
          Укажите заемщика, сумму и описание займа.
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        {isAdmin && (
          <label className="form-field">
            <span>Кредитор</span>

            <select
              value={lenderId}
              onChange={(e) => setLenderId(e.target.value)}
              disabled={loading}
            >
              <option value="">
                Я (текущий администратор)
              </option>

              {lenderOptions.map((user) => (
                <option
                  key={user.id}
                  value={user.id}
                >
                  {formatUserName(user)}
                </option>
              ))}
            </select>
          </label>
        )}

        <label className="form-field">
          <span>Заемщик</span>

          <select
            value={borrowerId}
            onChange={(e) => setBorrowerId(e.target.value)}
            disabled={loading}
          >
            <option value="">
              Выберите заемщика
            </option>

            {borrowerOptions.map((user) => (
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
            disabled={loading}
          />
        </label>

        <label className="form-field">
          <span>Описание</span>

          <input
            type="text"
            placeholder="Например: до пятницы"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={loading}
          />
        </label>

        {error && <p className="form-error">{error}</p>}

        <button
          type="submit"
          className="full-width create-loan-button"
          disabled={loading}
        >
          {loading ? "Создание..." : "Создать займ"}
        </button>
      </form>
    </div>
  );
}

export default CreateLoanForm;