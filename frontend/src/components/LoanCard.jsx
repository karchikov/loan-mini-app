import { useState } from "react";

import RepaymentHistory from "./RepaymentHistory";
import RepayForm from "./RepayForm";

import { formatDate, formatMoney } from "../utils/formatters";

const LOAN_STATUS_LABELS = {
  draft: "Ожидает подтверждения кредитора",
  waiting_confirmation: "Ожидает подтверждения погашения",
  active: "Активен",
  partially_paid: "Частично погашен",
  paid: "Погашен",
  overdue: "Просрочен",
  cancelled: "Отменен",
  disputed: "Спорный",
  rejected: "Отклонен",
};

function formatUser(userData, fallbackId) {
  if (!userData) {
    return `Пользователь #${fallbackId}`;
  }

  const name =
    userData.first_name || `Пользователь #${fallbackId}`;

  const username = userData.username;

  if (username) {
    return `${name} (@${username})`;
  }

  return name;
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

function formatDateOnly(value) {
  if (!value) {
    return "начислений пока нет";
  }

  if (typeof value === "string" && value.includes("-")) {
    const [year, month, day] = value.split("-");

    if (year && month && day) {
      return `${day}.${month}.${year}`;
    }
  }

  return formatDate(value);
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
  onConfirmRepayment,
  onRejectRepayment,
}) {
  const [historyVisible, setHistoryVisible] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [processingRepaymentId, setProcessingRepaymentId] = useState(null);
  const [repaymentActionError, setRepaymentActionError] = useState("");

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

  const pendingRepayments = Array.isArray(loan.pending_repayments)
    ? loan.pending_repayments
    : [];

  const pendingRepaymentsCount =
    Number(
      loan.pending_repayments_count ||
        pendingRepayments.length ||
        0
    );

  const hasPendingRepayments =
    pendingRepaymentsCount > 0;

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
    (isAdmin || isLender) &&
    !hasPendingRepayments;

  const statusLabel =
    LOAN_STATUS_LABELS[loan.status] || loan.status;

  const currency = loan.currency || "RUB";

  const principalRemaining =
    loan.principal_remaining ?? loan.amount;

  const unpaidInterest =
    loan.unpaid_interest ?? 0;

  const markPaidButtonText =
    loan.status === "waiting_confirmation"
      ? "Подтвердить закрытие займа"
      : "Отметить как погашенный";

  function canManagePendingRepayment(repayment) {
    if (!repayment || !user) {
      return false;
    }

    if (isAdmin) {
      return true;
    }

    const wasSubmittedByCurrentUser =
      repayment.submitted_by_user_id &&
      repayment.submitted_by_user_id === user.id;

    return (
      isLender &&
      !isBorrower &&
      !wasSubmittedByCurrentUser
    );
  }

  function shouldShowBorrowerPendingNotice(repayment) {
    if (!repayment || !user || isAdmin) {
      return false;
    }

    const wasSubmittedByCurrentUser =
      repayment.submitted_by_user_id &&
      repayment.submitted_by_user_id === user.id;

    return isBorrower || wasSubmittedByCurrentUser;
  }

  async function handleConfirmPendingRepayment(repaymentId) {
    if (!onConfirmRepayment) {
      return;
    }

    try {
      setRepaymentActionError("");
      setProcessingRepaymentId(repaymentId);

      await onConfirmRepayment(loan.id, repaymentId);
    } catch (error) {
      console.error(error);
      setRepaymentActionError(
        "Не удалось подтвердить платеж. Попробуйте еще раз."
      );
    } finally {
      setProcessingRepaymentId(null);
    }
  }

  async function handleRejectPendingRepayment(repaymentId) {
    if (!onRejectRepayment) {
      return;
    }

    try {
      setRepaymentActionError("");
      setProcessingRepaymentId(repaymentId);

      await onRejectRepayment(loan.id, repaymentId);
    } catch (error) {
      console.error(error);
      setRepaymentActionError(
        "Не удалось отклонить платеж. Попробуйте еще раз."
      );
    } finally {
      setProcessingRepaymentId(null);
    }
  }

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
        {formatMoney(loan.amount, currency)}
      </div>

      <div className="loan-balance-box">
        <span>Остаток к погашению</span>
        <strong>
          {formatMoney(loan.remaining_balance, currency)}
        </strong>

        <p className="muted">
          Сумма включает тело долга и начисленные проценты.
        </p>
      </div>

      <div className="loan-balance-box">
        <span>Тело долга</span>
        <strong>
          {formatMoney(principalRemaining, currency)}
        </strong>

        <p className="muted">
          Остаток основного долга после подтвержденных платежей.
        </p>
      </div>

      <div className="loan-balance-box">
        <span>Начисленные проценты</span>
        <strong>
          {formatMoney(unpaidInterest, currency)}
        </strong>

        <p className="muted">
          Последнее начисление:{" "}
          {formatDateOnly(loan.last_interest_accrual_date)}
        </p>
      </div>

      {hasPendingRepayments && (
        <div className="loan-balance-box">
          <span>Платежи на подтверждении</span>

          <strong>
            {formatMoney(
              loan.pending_repayments_total || 0,
              currency,
            )}
          </strong>

          <p className="muted">
            Количество платежей: {pendingRepaymentsCount}
          </p>

          {repaymentActionError && (
            <p className="form-error">
              {repaymentActionError}
            </p>
          )}

          {pendingRepayments.length === 0 && (
            <p className="muted">
              Откройте историю погашений, чтобы посмотреть платежи.
            </p>
          )}

          {pendingRepayments.map((repayment) => {
            const isProcessing =
              processingRepaymentId === repayment.id;

            const canManage =
              canManagePendingRepayment(repayment);

            const showBorrowerNotice =
              shouldShowBorrowerPendingNotice(repayment);

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
                  <strong>Дата:</strong>{" "}
                  {formatDate(repayment.created_at)}
                </p>

                {showBorrowerNotice && (
                  <p className="muted">
                    Платеж отправлен кредитору на подтверждение.
                  </p>
                )}

                {canManage && (
                  <div className="loan-actions-stack">
                    <button
                      className="full-width"
                      disabled={isProcessing}
                      onClick={() =>
                        handleConfirmPendingRepayment(repayment.id)
                      }
                    >
                      {isProcessing
                        ? "Обработка..."
                        : "Подтвердить платеж"}
                    </button>

                    <button
                      className="full-width danger-button"
                      disabled={isProcessing}
                      onClick={() =>
                        handleRejectPendingRepayment(repayment.id)
                      }
                    >
                      Отклонить платеж
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div className="loan-body">
        <p>
          <strong>Заемщик:</strong> {borrowerName}
        </p>

        <p>
          <strong>Кредитор:</strong> {lenderName}
        </p>

        <p>
          <strong>Валюта:</strong> {currency}
        </p>

        <p>
          <strong>Ставка:</strong>{" "}
          {formatAnnualInterestRate(loan.annual_interest_rate)} годовых
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
          currency={currency}
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
        <RepaymentHistory
          repayments={repayments || []}
          currency={currency}
          loan={loan}
          user={user}
          isAdmin={isAdmin}
          onConfirmRepayment={onConfirmRepayment}
          onRejectRepayment={onRejectRepayment}
        />
      )}
    </div>
  );
}

export default LoanCard;