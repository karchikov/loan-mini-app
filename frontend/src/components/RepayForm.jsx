import { useRef, useState } from "react";

function RepayForm({ onRepay }) {
  const [amount, setAmount] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const amountInputRef = useRef(null);

  async function handleSubmit() {
    setError("");
    setSuccess("");

    const value = Number(amount);

    if (!value || value <= 0) {
      setError("Сумма должна быть больше 0");
      return;
    }

    try {
      amountInputRef.current?.blur();
      setLoading(true);

      await onRepay(value);

      setAmount("");
      setSuccess(
        "Платеж отправлен кредитору на подтверждение"
      );
    } catch (err) {
      console.error(err);

      setError(
        err.response?.data?.detail ||
          "Не удалось отправить платеж"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="repay-box">
      <input
        ref={amountInputRef}
        type="number"
        inputMode="decimal"
        placeholder="Сумма платежа"
        value={amount}
        disabled={loading}
        onChange={(e) => setAmount(e.target.value)}
      />

      {error && <p className="form-error">{error}</p>}

      {success && <p className="form-success">{success}</p>}

      <button onClick={handleSubmit} disabled={loading}>
        {loading ? "Обработка..." : "Отправить платеж"}
      </button>
    </div>
  );
}

export default RepayForm;
