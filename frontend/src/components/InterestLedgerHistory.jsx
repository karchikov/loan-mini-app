import { formatMoney } from "../utils/formatters";

function formatDateOnly(value) {
  if (!value) {
    return "Не указано";
  }

  if (typeof value === "string" && value.includes("-")) {
    const datePart = value.split("T")[0];
    const [year, month, day] = datePart.split("-");

    if (year && month && day) {
      return `${day}.${month}.${year}`;
    }
  }

  return String(value);
}

function formatAnnualInterestRate(value) {
  const rate = Number(value || 0);

  if (Number.isNaN(rate)) {
    return "0%";
  }

  return `${rate.toLocaleString("ru-RU", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })}%`;
}

function InterestLedgerHistory({
  ledgerEntries,
  currency = "RUB",
}) {
  return (
    <div className="repayment-history">
      <h3>История начисления процентов</h3>

      {ledgerEntries?.length === 0 && (
        <p className="muted">
          Начислений процентов пока нет
        </p>
      )}

      {ledgerEntries?.map((entry) => (
        <div
          key={entry.id}
          className="repayment-item"
        >
          <p>
            <strong>Дата начисления:</strong>{" "}
            {formatDateOnly(entry.accrual_date)}
          </p>

          <p>
            <strong>Тело долга на дату начисления:</strong>{" "}
            {formatMoney(
              entry.principal_amount || 0,
              currency,
            )}
          </p>

          <p>
            <strong>Годовая ставка:</strong>{" "}
            {formatAnnualInterestRate(entry.annual_interest_rate)}
          </p>

          <p>
            <strong>Начислено процентов:</strong>{" "}
            {formatMoney(
              entry.interest_amount || 0,
              currency,
            )}
          </p>

          <p>
            <strong>Оплачено процентов:</strong>{" "}
            {formatMoney(
              entry.paid_amount || 0,
              currency,
            )}
          </p>

          <p>
            <strong>Остаток начисленных процентов:</strong>{" "}
            {formatMoney(
              entry.unpaid_interest_amount || 0,
              currency,
            )}
          </p>
        </div>
      ))}
    </div>
  );
}

export default InterestLedgerHistory;