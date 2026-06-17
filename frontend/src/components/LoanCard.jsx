import { useState } from "react";

import RepaymentHistory from "./RepaymentHistory";
import RepayForm from "./RepayForm";

import { formatMoney } from "../utils/formatters";

const LOAN_STATUS_LABELS = {
  draft: "Ожидает подтверждения кредитора",
  waiting_confirmation: "Ожидает подтверждения погашения",
  active: "Активен",
  partially_paid: "Частично погашен",
  paid: "Погашен",
  overdue: "Просрочен",
  cancelled: "Отменён",
  disputed: "Спорный",
  rejected: "Отклонён",
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
  onLoadRepayments,
  onConfirm,
  onReject,
  onMarkPaid,
  onRepay,
}) {
  const [historyVisible, setHistoryVisible] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);

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
      loan.status === "partially_paid" ||
      loan.status === "waiting_confirmation") &&
    (isAdmin || isLender);

  const statusLabel =
    LOAN_STATUS_LABELS[loan.status] || loan.status;

  const markPaidButtonText =
    loan.status === "waiting_confirmation"
      ? "Подтвердить закрытие займа"
      : "Отметить как погашенный";

  async function handleToggleHistory() {
    const nextVisible = !historyVisible;

    setHistoryVisible(nextVisible);

    if (
      nextVisible &&
      !repayments &&
      onLoadRepayments
    ) {
      try {
        setHistoryLoading(true);

        await onLoadRepayments(loan.id);
      } catch (error) {
        console.error(error);
      } finally {
        setHistoryLoading(false);
      }
    }
  }

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
          <strong>Заёмщик:</strong> {borrowerName}
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
        <div className="actions loan-actions">
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

      <div className="loan-actions-stack">
        {canMarkPaid && (
          <button
            className="full-width"
            onClick={() => onMarkPaid(loan.id)}
          >
            {markPaidButtonText}
          </button>
        )}

        <button
          className="full-width secondary-button"
          onClick={handleToggleHistory}
        >
          {historyVisible
            ? "Скрыть историю погашений"
            : "Показать историю погашений"}
        </button>
      </div>

      {historyLoading && (
        <p className="muted">Загружаем историю...</p>
      )}

      {historyVisible && !historyLoading && (
        <RepaymentHistory repayments={repayments || []} />
      )}
    </div>
  );
}

export default LoanCard;