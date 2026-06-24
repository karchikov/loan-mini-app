import { useMemo } from "react";

import EmptyState from "../components/EmptyState";
import LoanCard from "../components/LoanCard";

const ACTIVE_LOAN_STATUSES = [
  "draft",
  "active",
  "partially_paid",
  "waiting_confirmation",
];

const CLOSED_LOAN_STATUSES = [
  "paid",
  "rejected",
  "cancelled",
  "expired",
];

function getTodayUtcDateString() {
  const now = new Date();
  const year = now.getUTCFullYear();
  const month = String(now.getUTCMonth() + 1).padStart(2, "0");
  const day = String(now.getUTCDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function getLoanDueDateString(loan) {
  if (!loan?.due_date || typeof loan.due_date !== "string") {
    return "";
  }

  return loan.due_date.split("T")[0];
}

function isDraftLoanExpiredByUtcDate(loan) {
  if (loan.status !== "draft") {
    return false;
  }

  const dueDateString = getLoanDueDateString(loan);

  if (!dueDateString) {
    return false;
  }

  return dueDateString < getTodayUtcDateString();
}

function LoansPage({
  mode,
  loans,
  user,
  isAdmin,
  repayments,
  onLoadRepayments,
  onConfirm,
  onReject,
  onMarkPaid,
  onRepay,
  onConfirmRepayment,
  onRejectRepayment,
}) {
  const filteredLoans = useMemo(() => {
    const sorted = [...loans].sort((a, b) => b.id - a.id);

    if (mode === "paid") {
      return sorted.filter((loan) =>
        CLOSED_LOAN_STATUSES.includes(loan.status) ||
        isDraftLoanExpiredByUtcDate(loan)
      );
    }

    return sorted.filter((loan) =>
      ACTIVE_LOAN_STATUSES.includes(loan.status) &&
      !isDraftLoanExpiredByUtcDate(loan)
    );
  }, [loans, mode]);

  const title =
    mode === "paid" ? "Погашенные займы" : "Активные займы";

  const emptyTitle =
    mode === "paid"
      ? "Погашенных займов пока нет"
      : "Активных займов пока нет";

  const emptyText =
    mode === "paid"
      ? "Здесь будут отображаться погашенные, отклоненные, отмененные и истекшие заявки."
      : "Здесь будут отображаться займы, которые ожидают подтверждения, активны или погашены частично.";

  return (
    <div>
      <h2 className="page-title">
        {title}
      </h2>

      {filteredLoans.length === 0 && (
        <EmptyState
          title={emptyTitle}
          text={emptyText}
        />
      )}

      {filteredLoans.map((loan) => (
        <LoanCard
          key={loan.id}
          loan={loan}
          user={user}
          isAdmin={isAdmin}
          repayments={repayments[loan.id]}
          onLoadRepayments={onLoadRepayments}
          onConfirm={onConfirm}
          onReject={onReject}
          onMarkPaid={onMarkPaid}
          onRepay={onRepay}
          onConfirmRepayment={onConfirmRepayment}
          onRejectRepayment={onRejectRepayment}
        />
      ))}
    </div>
  );
}

export default LoansPage;