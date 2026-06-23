import { useState } from "react";

import InterestLedgerHistory from "./InterestLedgerHistory";
import RepaymentHistory from "./RepaymentHistory";
import RepayForm from "./RepayForm";

import { getInterestLedger } from "../api/loans";
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
  expired: "Срок заявки истек",
};

const CLOSED_LOAN_STATUSES = [
  "paid",
  "cancelled",
  "rejected",
  "expired",
];

const ISSUED_LOAN_STATUSES = [
  "active",
  "partially_paid",
  "waiting_confirmation",
  "overdue",
];

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

function formatDateValue(value, emptyLabel = "Не указано") {
  if (!value) {
    return emptyLabel;
  }

  if (typeof value === "string" && value.includes("-")) {
    const datePart = value.split("T")[0];
    const [year, month, day] = datePart.split("-");

    if (year && month && day) {
      return `${day}.${month}.${year}`;
    }
  }

  return formatDate(value);
}

function parseDateOnly(value) {
  if (!value || typeof value !== "string") {
    return null;
  }

  const datePart = value.split("T")[0];
  const parts = datePart.split("-");

  if (parts.length !== 3) {
    return null;
  }

  const [year, month, day] = parts.map(Number);

  if (!year || !month || !day) {
    return null;
  }

  return new Date(year, month - 1, day);
}

function getTodayDateOnly() {
  const today = new Date();

  today.setHours(0, 0, 0, 0);

  return today;
}

function getOverdueDays(dueDate) {
  if (!dueDate) {
    return 0;
  }

  const today = getTodayDateOnly();
  const diffMs = today.getTime() - dueDate.getTime();

  if (diffMs <= 0) {
    return 0;
  }

  return Math.floor(diffMs / (1000 * 60 * 60 * 24));
}

function formatDaysWord(days) {
  const absDays = Math.abs(days);
  const lastDigit = absDays % 10;
  const lastTwoDigits = absDays % 100;

  if (lastTwoDigits >= 11 && lastTwoDigits <= 14) {
    return "дней";
  }

  if (lastDigit === 1) {
    return "день";
  }

  if (lastDigit >= 2 && lastDigit <= 4) {
    return "дня";
  }

  return "дней";
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

  const [interestLedgerVisible, setInterestLedgerVisible] = useState(false);
  const [interestLedgerLoading, setInterestLedgerLoading] = useState(false);
  const [interestLedgerError, setInterestLedgerError] = useState("");
  const [interestLedgerEntries, setInterestLedgerEntries] = useState(null);

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

  const dueDate = parseDateOnly(loan.due_date);
  const overdueDays = getOverdueDays(dueDate);

  const isDraftExpiredLocally =
    loan.status === "draft" &&
    overdueDays > 0;

  const isExpiredLoan =
    loan.status === "expired" ||
    isDraftExpiredLocally;

  const isClosedLoan =
    CLOSED_LOAN_STATUSES.includes(loan.status) ||
    isExpiredLoan;

  const isIssuedLoan =
    ISSUED_LOAN_STATUSES.includes(loan.status);

  const isOverdue =
    overdueDays > 0 &&
    isIssuedLoan &&
    !isClosedLoan;

  const displayStatus =
    isExpiredLoan ? "expired" : loan.status;

  const canConfirmOrReject =
    loan.status === "draft" &&
    !isDraftExpiredLocally &&
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
    LOAN_STATUS_LABELS[displayStatus] || displayStatus;

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

  async function loadInterestLedger(force = false) {
    if (!force && interestLedgerEntries) {
      return;
    }

    try {
      setInterestLedgerError("");
      setInterestLedgerLoading(true);

      const entries = await getInterestLedger(loan.id);

      setInterestLedgerEntries(
        Array.isArray(entries) ? entries : []
      );
    } catch (error) {
      console.error(error);

      setInterestLedgerError(
        "Не удалось загрузить историю процентов. Попробуйте еще раз."
      );
    } finally {
      setInterestLedgerLoading(false);
    }
  }

  async function handleConfirmPendingRepayment(repaymentId) {
    if (!onConfirmRepayment) {
      return;
    }

    try {
      setRepaymentActionError("");
      setProcessingRepaymentId(repaymentId);

      await onConfirmRepayment(loan.id, repaymentId);

      if (interestLedgerVisible) {
        await loadInterestLedger(true);
      }
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

  async function handleMarkPaid() {
    if (!onMarkPaid) {
      return;
    }

    await onMarkPaid(loan.id);

    if (interestLedgerVisible) {
      await loadInterestLedger(true);
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

  async function handleToggleInterestLedger() {
    const nextVisible = !interestLedgerVisible;

    setInterestLedgerVisible(nextVisible);

    if (nextVisible) {
      await loadInterestLedger(false);
    }
  }

  return (
    <div
      className={
        isExpiredLoan
          ? "card loan-card loan-card-expired"
          : isOverdue
            ? "card loan-card loan-card-overdue"
            : "card loan-card"
      }
    >
      <div className="loan-header">
        <div>
          <p className="loan-id">Займ №{loan.id}</p>

          <p className={`loan-status ${displayStatus}`}>
            {statusLabel}
          </p>
        </div>

        {isOverdue && (
          <div className="loan-overdue-badge">
            Займ просрочен
          </div>
        )}

        {isExpiredLoan && (
          <div className="loan-expired-badge">
            Срок заявки истек
          </div>
        )}
      </div>

      <div className="loan-main-amount">
        {formatMoney(loan.amount, currency)}
      </div>

      <div className="loan-info-panel">
        <h3 className="loan-info-title">
          Детали займа
        </h3>

        <div className="loan-info-row">
          <span className="loan-info-label">
            Сумма займа
          </span>

          <strong className="loan-info-value">
            {formatMoney(loan.amount, currency)}
          </strong>
        </div>

        <div className="loan-info-row">
          <span className="loan-info-label">
            Тело долга
          </span>

          <strong className="loan-info-value">
            {formatMoney(principalRemaining, currency)}
          </strong>
        </div>

        <div className="loan-info-row">
          <span className="loan-info-label">
            Начисленные проценты
          </span>

          <strong className="loan-info-value">
            {formatMoney(unpaidInterest, currency)}
          </strong>
        </div>

        <div className="loan-info-row">
          <span className="loan-info-label">
            Остаток к погашению
          </span>

          <strong className="loan-info-value">
            {formatMoney(loan.remaining_balance, currency)}
          </strong>
        </div>

        <div className="loan-info-row">
          <span className="loan-info-label">
            Ставка
          </span>

          <strong className="loan-info-value">
            {formatAnnualInterestRate(loan.annual_interest_rate)} годовых
          </strong>
        </div>

        <div className="loan-info-row">
          <span className="loan-info-label">
            Дата выдачи
          </span>

          <strong className="loan-info-value">
            {formatDateValue(loan.created_at)}
          </strong>
        </div>

        <div
          className={
            isOverdue
              ? "loan-info-row loan-overdue-row"
              : isExpiredLoan
                ? "loan-info-row loan-expired-row"
                : "loan-info-row"
          }
        >
          <span className="loan-info-label">
            Срок возврата
          </span>

          <div className="loan-info-value">
            <strong
              className={
                isOverdue
                  ? "loan-overdue-value"
                  : ""
              }
            >
              {formatDateValue(loan.due_date)}
            </strong>

            {isOverdue && (
              <p className="loan-overdue-text">
                Займ просрочен
                <br />
                Просрочен на {overdueDays} {formatDaysWord(overdueDays)}
              </p>
            )}

            {isExpiredLoan && (
              <p className="loan-expired-text">
                Заявка не была подтверждена кредитором до срока возврата
              </p>
            )}
          </div>
        </div>

        <div className="loan-info-row">
          <span className="loan-info-label">
            Последнее начисление процентов
          </span>

          <strong className="loan-info-value">
            {formatDateValue(
              loan.last_interest_accrual_date,
              "начислений пока нет",
            )}
          </strong>
        </div>
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
            onClick={handleMarkPaid}
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

        <button
          className="full-width secondary-button"
          onClick={handleToggleInterestLedger}
        >
          {interestLedgerVisible
            ? "Скрыть историю процентов"
            : "Показать историю процентов"}
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

      {interestLedgerLoading && (
        <p className="muted">Загружаем историю процентов...</p>
      )}

      {interestLedgerError && (
        <p className="form-error">
          {interestLedgerError}
        </p>
      )}

      {interestLedgerVisible && !interestLedgerLoading && (
        <InterestLedgerHistory
          ledgerEntries={interestLedgerEntries || []}
          currency={currency}
        />
      )}
    </div>
  );
}

export default LoanCard;