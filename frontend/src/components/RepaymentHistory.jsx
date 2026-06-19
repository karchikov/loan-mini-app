import { useState } from "react";

import { formatDate, formatMoney } from "../utils/formatters";

const REPAYMENT_STATUS_LABELS = {
  pending: "Ожидает подтверждения",
  confirmed: "Подтвержден",
  rejected: "Отклонен",
};

function getRepaymentActionErrorMessage(error) {
  const message = error?.message || "";

  if (
    message.includes("403") ||
    message.includes("Borrower cannot confirm own repayment") ||
    message.includes("Borrower cannot reject own repayment")
  ) {
    return "Заемщик не может подтвердить или отклонить собственный платеж. Подтверждение должен выполнить кредитор.";
  }

  return "Не удалось выполнить действие с платежом. Попробуйте еще раз.";
}

function RepaymentHistory({
  repayments,
  currency = "RUB",
  loan,
  user,
  isAdmin,
  onConfirmRepayment,
  onRejectRepayment,
}) {
  const [processingId, setProcessingId] = useState(null);
  const [actionError, setActionError] = useState("");

  async function handleConfirm(repaymentId) {
    if (!onConfirmRepayment || !loan) {
      return;
    }

    try {
      setActionError("");
      setProcessingId(repaymentId);

      await onConfirmRepayment(loan.id, repaymentId);
    } catch (error) {
      console.error(error);
      setActionError(getRepaymentActionErrorMessage(error));
    } finally {
      setProcessingId(null);
    }
  }

  async function handleReject(repaymentId) {
    if (!onRejectRepayment || !loan) {
      return;
    }

    try {
      setActionError("");
      setProcessingId(repaymentId);

      await onRejectRepayment(loan.id, repaymentId);
    } catch (error) {
      console.error(error);
      setActionError(getRepaymentActionErrorMessage(error));
    } finally {
      setProcessingId(null);
    }
  }

  return (
    <div className="repayment-history">
      <h3>История погашений</h3>

      {actionError && (
        <p className="error-message">
          {actionError}
        </p>
      )}

      {repayments?.length === 0 && (
        <p className="muted">
          Погашений пока нет
        </p>
      )}

      {repayments?.map((repayment) => {
        const status =
          repayment.status || "confirmed";

        const statusLabel =
          REPAYMENT_STATUS_LABELS[status] || status;

        const isPending = status === "pending";

        const isCurrentUserBorrower =
          loan &&
          user &&
          user.id === loan.borrower_id;

        const isCurrentUserLender =
          loan &&
          user &&
          user.id === loan.lender_id;

        const wasSubmittedByCurrentUser =
          user &&
          repayment.submitted_by_user_id &&
          user.id === repayment.submitted_by_user_id;

        const canManageRepayment =
          isPending &&
          loan &&
          user &&
          (isAdmin || isCurrentUserLender) &&
          !isCurrentUserBorrower &&
          !wasSubmittedByCurrentUser;

        const shouldShowBorrowerRestriction =
          isPending &&
          user &&
          (isCurrentUserBorrower || wasSubmittedByCurrentUser);

        const isProcessing =
          processingId === repayment.id;

        return (
          <div
            key={repayment.id}
            className="repayment-item"
          >
            <p>
              <strong>Сумма:</strong>{" "}
              {formatMoney(
                repayment.amount,
                currency,
              )}
            </p>

            <p>
              <strong>Статус:</strong>{" "}
              {statusLabel}
            </p>

            <p>
              <strong>Дата:</strong>{" "}
              {formatDate(repayment.created_at)}
            </p>

            {status === "confirmed" && (
              <>
                <p>
                  <strong>В проценты:</strong>{" "}
                  {formatMoney(
                    repayment.interest_amount || 0,
                    currency,
                  )}
                </p>

                <p>
                  <strong>В тело долга:</strong>{" "}
                  {formatMoney(
                    repayment.principal_amount || 0,
                    currency,
                  )}
                </p>
              </>
            )}

            {shouldShowBorrowerRestriction && (
              <p className="muted">
                Заемщик не может подтвердить собственный платеж.
                Подтверждение должен выполнить кредитор.
              </p>
            )}

            {canManageRepayment && (
              <div className="loan-actions-stack">
                <button
                  className="full-width"
                  disabled={isProcessing}
                  onClick={() => handleConfirm(repayment.id)}
                >
                  {isProcessing
                    ? "Обработка..."
                    : "Подтвердить платеж"}
                </button>

                <button
                  className="full-width danger-button"
                  disabled={isProcessing}
                  onClick={() => handleReject(repayment.id)}
                >
                  Отклонить платеж
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default RepaymentHistory;