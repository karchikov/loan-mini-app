import RepaymentHistory from "./RepaymentHistory";
import RepayForm from "./RepayForm";

import { formatMoney } from "../utils/formatters";

function LoanCard({
  loan,
  user,
  isAdmin,
  repayments,
  onConfirm,
  onReject,
  onMarkPaid,
  onRepay,
}) {
  const isBorrower = user.id === loan.borrower_id;
  const isLender = user.id === loan.lender_id;

  const canConfirmOrReject =
    loan.status === "draft" &&
    (isAdmin || isBorrower);

  const canRepay =
    (loan.status === "active" ||
      loan.status === "partially_paid") &&
    (isAdmin || isBorrower);

  const canMarkPaid =
    (loan.status === "active" ||
      loan.status === "partially_paid") &&
    (isAdmin || isLender);

  return (
    <div className="card loan-card">
      <div className="loan-header">
        <div>
          <p className="loan-id">Loan #{loan.id}</p>
          <p className={`loan-status ${loan.status}`}>
            {loan.status}
          </p>
        </div>

        <div className="loan-amount">
          {formatMoney(loan.amount)}
        </div>
      </div>

      <div className="loan-body">
        <p>
          <strong>Remaining:</strong>{" "}
          {formatMoney(loan.remaining_balance)}
        </p>

        <p>
          <strong>Borrower ID:</strong> {loan.borrower_id}
        </p>

        <p>
          <strong>Lender ID:</strong> {loan.lender_id}
        </p>

        <p>
          <strong>Description:</strong>{" "}
          {loan.description || "No description"}
        </p>
      </div>

      {canConfirmOrReject && (
        <div className="actions sticky-actions">
          <button onClick={() => onConfirm(loan.id)}>
            Confirm
          </button>

          <button
            className="danger-button"
            onClick={() => onReject(loan.id)}
          >
            Reject
          </button>
        </div>
      )}

      {canRepay && (
        <RepayForm
          onRepay={(amount) => onRepay(loan.id, amount)}
        />
      )}

      {canMarkPaid && (
        <button
          className="full-width sticky-actions"
          onClick={() => onMarkPaid(loan.id)}
        >
          Mark Paid
        </button>
      )}

      <RepaymentHistory repayments={repayments} />
    </div>
  );
}

export default LoanCard;