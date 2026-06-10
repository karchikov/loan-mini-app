import { formatDate, formatMoney } from "../utils/formatters";

function RepaymentHistory({ repayments }) {
  return (
    <div className="repayment-history">
      <h3>История погашений</h3>

      {repayments?.length === 0 && (
        <p className="muted">Погашений пока нет</p>
      )}

      {repayments?.map((repayment) => (
        <div key={repayment.id} className="repayment-item">
          <p>
            <strong>Сумма:</strong> {formatMoney(repayment.amount)}
          </p>

          <p>
            <strong>Дата:</strong> {formatDate(repayment.created_at)}
          </p>
        </div>
      ))}
    </div>
  );
}

export default RepaymentHistory;