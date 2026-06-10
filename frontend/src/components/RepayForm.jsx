import { useState } from "react";

function RepayForm({ onRepay }) {
  const [amount, setAmount] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit() {
    setError("");

    const value = Number(amount);

    if (!value || value <= 0) {
      setError("Сумма должна быть больше 0");
      return;
    }

    try {
      setLoading(true);

      await onRepay(value);

      setAmount("");
    } catch (err) {
      console.error(err);

      setError(
        err.response?.data?.detail ||
          "Не удалось создать погашение"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="repay-box">
      <input
        type="number"
        placeholder="Сумма погашения"
        value={amount}
        disabled={loading}
        onChange={(e) => setAmount(e.target.value)}
      />

      {error && <p className="form-error">{error}</p>}

      <button onClick={handleSubmit} disabled={loading}>
        {loading ? "Обработка..." : "Погасить часть"}
      </button>
    </div>
  );
}

export default RepayForm;