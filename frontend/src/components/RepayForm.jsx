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
        "Сумма возврата зафиксирована и ожидает подтверждения кредитором"
      );
    } catch (err) {
      console.error(err);

      setError(
        err.response?.data?.detail ||
          "Не удалось зафиксировать возврат"
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
        min="0"
        step="0.01"
        inputMode="decimal"
        placeholder="Сумма возврата"
        value={amount}
        disabled={loading}
        onChange={(e) => setAmount(e.target.value)}
      />

      {error && <p className="form-error">{error}</p>}

      {success && <p className="form-success">{success}</p>}

      <button onClick={handleSubmit} disabled={loading}>
        {loading ? "Фиксируем..." : "Зафиксировать возврат"}
      </button>
    </div>
  );
}

export default RepayForm;
