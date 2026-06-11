import RepaymentHistory from "./RepaymentHistory";
import RepayForm from "./RepayForm";

import { formatMoney } from "../utils/formatters";

const LOAN_STATUS_LABELS = {
  draft: "Ожидает подтверждения кредитора",
  active: "Активен",
  partially_paid: "Частично погашен",
  paid: "Погашен",
  rejected: "Отклонен",
};

function formatUser(userData, fallbackId) {
  if (!userData) {
    return `Пользователь #${fallbackId}`;
  }

  const name = userData.first_name || `Пользователь #${fallbackId}`;
  const username = userData.username;

  if (username) {
    return `${name} (@${username})`;
  }

  return name;
}

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

  const borrowerName = formatUser(
    loan.borrower,
    loan.borrower_id,
  );

  const lenderName = formatUser(
    loan.lender,
    loan.lender_id,
  );

  const canConfirmOrReject =
    loan.status === "draft" &&
    (isAdmin || isLender);

  const canRepay =
    (loan.status === "active" ||
      loan.status === "partially_paid") &&
    (isAdmin || isBorrower);

  const canMarkPaid =
    (loan.status === "active" ||
      loan.status === "partially_paid") &&
    (isAdmin || isLender);

  const statusLabel =
    LOAN_STATUS_LABELS[loan.status] || loan.status;

  return (
    <div className="card loan-card">
      <div className="loan-header">
        <div>
          <p className="loan-id">Займ №{loan.id}</p>

          <p className={`loan-status ${loan.status}`}>
            {statusLabel}
          </p>
        </div>
      </div>

      <div className="loan-main-amount">
        {formatMoney(loan.amount)}
      </div>

      <div className="loan-balance-box">
        <span>Остаток к погашению</span>
        <strong>
          {formatMoney(loan.remaining_balance)}
        </strong>
      </div>

      <div className="loan-body">
        <p>
          <strong>Заемщик:</strong> {borrowerName}
        </p>

        <p>
          <strong>Кредитор:</strong> {lenderName}
        </p>

        <p>
          <strong>Описание:</strong>{" "}
          {loan.description || "Без описания"}
        </p>
      </div>

      {canConfirmOrReject && (
        <div className="actions sticky-actions">
          <button onClick={() => onConfirm(loan.id)}>
            Подтвердить
          </button>

          <button
            className="danger-button"
            onClick={() => onReject(loan.id)}
          >
            Отклонить
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
          Отметить как погашенный
        </button>
      )}

      <RepaymentHistory repayments={repayments} />
    </div>
  );
}

export default LoanCard;