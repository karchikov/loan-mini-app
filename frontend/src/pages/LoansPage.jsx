import { useMemo } from "react";

import EmptyState from "../components/EmptyState";
import LoanCard from "../components/LoanCard";

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
      return sorted.filter((loan) => loan.status === "paid");
    }

    return sorted.filter((loan) => {
      return (
        loan.status === "draft" ||
        loan.status === "active" ||
        loan.status === "partially_paid" ||
        loan.status === "waiting_confirmation"
      );
    });
  }, [loans, mode]);

  const title =
    mode === "paid" ? "Погашенные займы" : "Активные займы";

  const emptyTitle =
    mode === "paid"
      ? "Погашенных займов пока нет"
      : "Активных займов пока нет";

  const emptyText =
    mode === "paid"
      ? "Здесь будут отображаться полностью погашенные займы."
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