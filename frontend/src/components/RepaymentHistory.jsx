import { formatDate, formatMoney } from "../utils/formatters";

function RepaymentHistory({ repayments }) {
  return (
    <div className="repayment-history">
      <h3>Repayment History</h3>

      {repayments?.length === 0 && (
        <p className="muted">No repayments yet</p>
      )}

      {repayments?.map((repayment) => (
        <div key={repayment.id} className="repayment-item">
          <p>
            <strong>Amount:</strong> {formatMoney(repayment.amount)}
          </p>

          <p>
            <strong>Date:</strong> {formatDate(repayment.created_at)}
          </p>
        </div>
      ))}
    </div>
  );
}

export default RepaymentHistory;