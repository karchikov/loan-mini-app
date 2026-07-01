import { useEffect, useState } from "react";

import InterestLedgerHistory from "./InterestLedgerHistory";
import RepaymentHistory from "./RepaymentHistory";
import RepayForm from "./RepayForm";

import { getInterestLedger } from "../api/loans";
import { formatDate, formatMoney } from "../utils/formatters";

const LOAN_STATUS_LABELS = {
  draft: "Заявка у кредитора",
  waiting_confirmation: "Ожидает закрытия кредитором",
  funding_pending: "Ожидает подтверждения заемщика",
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
  "overdue",
];

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

function getNextStepText({
  status,
  isBorrower,
  isLender,
  isAdmin,
  isExpiredLoan,
  hasPendingRepayments,
}) {
  if (isExpiredLoan) {
    return "Заявка не была завершена до срока возврата. Создайте новую заявку, если договоренность актуальна.";
  }

  if (hasPendingRepayments) {
    if (isBorrower) {
      return "Зафиксированный возврат ожидает подтверждения кредитором.";
    }

    if (isLender || isAdmin) {
      return "Проверьте фактическое получение суммы вне приложения и подтвердите или отклоните возврат.";
    }
  }

  if (status === "draft") {
    if (isLender || isAdmin) {
      return "Проверьте заявку. Если готовы передать деньги вне приложения, подтвердите готовность.";
    }

    return "Заявка отправлена кредитору. Ожидайте подтверждения готовности.";
  }

  if (status === "funding_pending") {
    if (isBorrower || isAdmin) {
      return "Подтвердите получение только после фактического получения денег вне приложения.";
    }

    return "Готовность зафиксирована. Ожидаем подтверждения заемщика после передачи денег вне приложения.";
  }

  if (status === "active" || status === "partially_paid") {
    if (isBorrower) {
      return "Если вы вернули часть суммы вне приложения, зафиксируйте возврат в карточке.";
    }

    if (isLender || isAdmin) {
      return "Если заемщик вернул сумму вне приложения, подтвердите полученный возврат.";
    }

    return "Займ активен.";
  }

  if (status === "waiting_confirmation") {
    if (isLender || isAdmin) {
      return "Проверьте фактическое получение полной суммы и подтвердите закрытие займа.";
    }

    return "Ожидаем подтверждения закрытия займа кредитором.";
  }

  if (status === "paid") {
    return "Займ закрыт.";
  }

  if (status === "rejected") {
    return "Заявка отклонена.";
  }

  return "";
}

function getApiErrorText(error, fallbackText) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => item?.msg)
      .filter(Boolean)
      .join(". ");
  }

  return fallbackText;
}

function LoanCard({
  loan,
  user,
  isAdmin,
  repayments,
  fundingActivationCode,
  onLoadRepayments,
  onConfirm,
  onRegenerateActivationCode,
  onActivateLoan,
  onActivateLoanByConfirmation,
  onReject,
  onMarkPaid,
  onRepay,
  onConfirmRepayment,
  onRejectRepayment,
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [historyVisible, setHistoryVisible] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [processingRepaymentId, setProcessingRepaymentId] = useState(null);
  const [repaymentActionError, setRepaymentActionError] = useState("");
  const [interestLedgerVisible, setInterestLedgerVisible] = useState(false);
  const [interestLedgerLoading, setInterestLedgerLoading] = useState(false);
  const [interestLedgerError, setInterestLedgerError] = useState("");
  const [interestLedgerEntries, setInterestLedgerEntries] = useState(null);
  const [activationCodeInput, setActivationCodeInput] = useState("");
  const [activationActionError, setActivationActionError] = useState("");
  const [activationActionSuccess, setActivationActionSuccess] = useState("");
  const [activationProcessing, setActivationProcessing] = useState(false);
  const [regenerateProcessing, setRegenerateProcessing] = useState(false);
  const [enhancedConfirmationVisible, setEnhancedConfirmationVisible] =
    useState(false);

  const isBorrower = user.id === loan.borrower_id;
  const isLender = user.id === loan.lender_id;
  const isFundingPending = loan.status === "funding_pending";

  const borrowerName = formatUser(
    loan.borrower,
    loan.borrower_id,
  );

  const lenderName = formatUser(
    loan.lender,
    loan.lender_id,
  );

  const summaryTitle = isBorrower
    ? `Кредитор: ${lenderName}`
    : isLender
      ? `Заемщик: ${borrowerName}`
      : isAdmin
        ? `${borrowerName} → ${lenderName}`
        : `Займ №${loan.id}`;

  const pendingRepayments = Array.isArray(loan.pending_repayments)
    ? loan.pending_repayments
    : [];

  const pendingRepaymentsCount = Number(
    loan.pending_repayments_count || pendingRepayments.length || 0,
  );

  const hasPendingRepayments = pendingRepaymentsCount > 0;

  const dueDate = parseDateOnly(loan.due_date);
  const overdueDays = getOverdueDays(dueDate);

  const isRequestExpiredLocally =
    (
      loan.status === "draft" ||
      loan.status === "funding_pending"
    ) &&
    overdueDays > 0;

  const isExpiredLoan =
    loan.status === "expired" || isRequestExpiredLocally;

  const isClosedLoan =
    CLOSED_LOAN_STATUSES.includes(loan.status) || isExpiredLoan;

  const isIssuedLoan =
    ISSUED_LOAN_STATUSES.includes(loan.status);

  const isOverdue =
    overdueDays > 0 && isIssuedLoan && !isClosedLoan;

  const displayStatus = isExpiredLoan
    ? "expired"
    : loan.status;

  const canConfirmOrReject =
    loan.status === "draft" &&
    !isRequestExpiredLocally &&
    (isAdmin || isLender);

  const canRegenerateActivationCode =
    isFundingPending &&
    !isExpiredLoan &&
    (isAdmin || isLender);

  const canActivateLoan =
    isFundingPending &&
    !isExpiredLoan &&
    (isAdmin || isBorrower);

  const canRepay =
    (
      loan.status === "active" ||
      loan.status === "partially_paid"
    ) &&
    (isAdmin || isBorrower);

  const canMarkPaid =
    (
      loan.status === "active" ||
      loan.status === "partially_paid"
    ) &&
    (isAdmin || isLender) &&
    !hasPendingRepayments;

  const statusLabel = LOAN_STATUS_LABELS[displayStatus] || displayStatus;
  const currency = loan.currency || "RUB";
  const principalRemaining = loan.principal_remaining ?? loan.amount;
  const unpaidInterest = loan.unpaid_interest ?? 0;

  const markPaidButtonText =
    loan.status === "waiting_confirmation"
      ? "Подтвердить закрытие займа"
      : "Подтвердить полное погашение";

  const nextStepText = getNextStepText({
    status: loan.status,
    isBorrower,
    isLender,
    isAdmin,
    isExpiredLoan,
    hasPendingRepayments,
  });

  useEffect(() => {
    if (
      !isExpiredLoan &&
      (
        isFundingPending ||
        hasPendingRepayments
      ) &&
      (
        isBorrower ||
        isLender ||
        isAdmin
      )
    ) {
      setIsExpanded(true);
    }
  }, [
    isFundingPending,
    hasPendingRepayments,
    isExpiredLoan,
    isBorrower,
    isLender,
    isAdmin,
  ]);

  function toggleExpanded() {
    setIsExpanded((currentValue) => !currentValue);
  }

  function handleSummaryKeyDown(event) {
    if (
      event.key === "Enter" ||
      event.key === " "
    ) {
      event.preventDefault();
      toggleExpanded();
    }
  }

  function handleActivationCodeInputChange(event) {
    const value = event.target.value.replace(/\D/g, "").slice(0, 4);

    setActivationCodeInput(value);
    setActivationActionError("");
    setActivationActionSuccess("");
  }

  async function handleRegenerateActivationCode() {
    if (!onRegenerateActivationCode) {
      return;
    }

    try {
      setActivationActionError("");
      setActivationActionSuccess("");
      setRegenerateProcessing(true);

      await onRegenerateActivationCode(loan.id);

      setActivationActionSuccess(
        "Новый код сгенерирован. Старый код больше не действует.",
      );
    } catch (error) {
      console.error(error);

      setActivationActionError(
        getApiErrorText(
          error,
          "Не удалось сгенерировать новый код. Попробуйте еще раз.",
        ),
      );
    } finally {
      setRegenerateProcessing(false);
    }
  }

  async function handleActivateLoan() {
    if (!onActivateLoan) {
      return;
    }

    if (activationCodeInput.length !== 4) {
      setActivationActionError("Введите 4-значный код активации.");
      return;
    }

    try {
      setActivationActionError("");
      setActivationActionSuccess("");
      setActivationProcessing(true);

      await onActivateLoan(loan.id, activationCodeInput);

      setActivationCodeInput("");
      setActivationActionSuccess(
        "Получение денег подтверждено. Займ активирован.",
      );
    } catch (error) {
      console.error(error);

      setActivationActionError(
        getApiErrorText(
          error,
          "Не удалось активировать займ. Проверьте код и попробуйте еще раз.",
        ),
      );
    } finally {
      setActivationProcessing(false);
    }
  }

  async function handleActivateLoanByConfirmation() {
    if (!onActivateLoanByConfirmation) {
      return;
    }

    try {
      setActivationActionError("");
      setActivationActionSuccess("");
      setActivationProcessing(true);

      await onActivateLoanByConfirmation(loan.id);

      setActivationCodeInput("");
      setEnhancedConfirmationVisible(false);
      setActivationActionSuccess(
        "Получение денег подтверждено. Займ активирован.",
      );
    } catch (error) {
      console.error(error);

      setActivationActionError(
        getApiErrorText(
          error,
          "Не удалось подтвердить получение денег. Попробуйте еще раз.",
        ),
      );
    } finally {
      setActivationProcessing(false);
    }
  }

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
        Array.isArray(entries) ? entries : [],
      );
    } catch (error) {
      console.error(error);

      setInterestLedgerError(
        "Не удалось загрузить историю процентов. Попробуйте еще раз.",
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
        "Не удалось подтвердить возврат. Попробуйте еще раз.",
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
        "Не удалось отклонить возврат. Попробуйте еще раз.",
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
    <article
      className={`card loan-card ${
        isOverdue ? "loan-card-overdue" : ""
      } ${
        isExpiredLoan ? "loan-card-expired" : ""
      } ${
        isFundingPending && !isExpiredLoan ? "loan-card-funding-pending" : ""
      }`}
    >
      <div
        className="loan-header"
        role="button"
        tabIndex={0}
        onClick={toggleExpanded}
        onKeyDown={handleSummaryKeyDown}
        aria-expanded={isExpanded}
        style={{ cursor: "pointer" }}
      >
        <div>
          <p className="loan-id">
            {summaryTitle}
          </p>

          <p className={`loan-status ${displayStatus}`}>
            {statusLabel}
          </p>

          {nextStepText && (
            <p className="loan-next-step">
              {nextStepText}
            </p>
          )}

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

        <div className="loan-amount">
          {formatMoney(loan.amount, currency)}
        </div>
      </div>

      {isExpanded && (
        <>
          <div className="loan-info-panel">
            <h3 className="loan-info-title">
              Детали займа
            </h3>

            <div className="loan-info-row">
              <span className="loan-info-label">
                Технический номер
              </span>

              <span className="loan-info-value">
                №{loan.id}
              </span>
            </div>

            <div className="loan-info-row">
              <span className="loan-info-label">
                Сумма займа
              </span>

              <span className="loan-info-value">
                {formatMoney(loan.amount, currency)}
              </span>
            </div>

            <div className="loan-info-row">
              <span className="loan-info-label">
                Тело долга
              </span>

              <span className="loan-info-value">
                {formatMoney(principalRemaining, currency)}
              </span>
            </div>

            <div className="loan-info-row">
              <span className="loan-info-label">
                Начисленные проценты
              </span>

              <span className="loan-info-value">
                {formatMoney(unpaidInterest, currency)}
              </span>
            </div>

            <div className="loan-info-row">
              <span className="loan-info-label">
                Остаток к погашению
              </span>

              <span className="loan-info-value">
                {formatMoney(loan.remaining_balance, currency)}
              </span>
            </div>

            <div className="loan-info-row">
              <span className="loan-info-label">
                Ставка
              </span>

              <span className="loan-info-value">
                {formatAnnualInterestRate(loan.annual_interest_rate)} годовых
              </span>
            </div>

            <div className="loan-info-row">
              <span className="loan-info-label">
                Дата создания заявки
              </span>

              <span className="loan-info-value">
                {formatDateValue(loan.created_at)}
              </span>
            </div>

            {loan.lender_confirmed_at && (
              <div className="loan-info-row">
                <span className="loan-info-label">
                  Дата подтверждения кредитором
                </span>

                <span className="loan-info-value">
                  {formatDateValue(loan.lender_confirmed_at)}
                </span>
              </div>
            )}

            {loan.borrower_received_at && (
              <div className="loan-info-row">
                <span className="loan-info-label">
                  Дата подтверждения получения денег
                </span>

                <span className="loan-info-value">
                  {formatDateValue(loan.borrower_received_at)}
                </span>
              </div>
            )}

            <div
              className={`loan-info-row ${
                isOverdue ? "loan-overdue-row" : ""
              } ${
                isExpiredLoan ? "loan-expired-row" : ""
              }`}
            >
              <span className="loan-info-label">
                Срок возврата
              </span>

              <span className="loan-info-value">
                <span className={isOverdue ? "loan-overdue-value" : ""}>
                  {formatDateValue(loan.due_date)}
                </span>

                {isOverdue && (
                  <p className="loan-overdue-text">
                    Займ просрочен. Просрочен на {overdueDays}{" "}
                    {formatDaysWord(overdueDays)}.
                  </p>
                )}

                {isExpiredLoan && (
                  <p className="loan-expired-text">
                    Заявка не была полностью подтверждена до срока возврата
                  </p>
                )}
              </span>
            </div>

            <div className="loan-info-row">
              <span className="loan-info-label">
                Последнее начисление процентов
              </span>

              <span className="loan-info-value">
                {formatDateValue(
                  loan.last_interest_accrual_date,
                  "начислений пока нет",
                )}
              </span>
            </div>

            {hasPendingRepayments && (
              <div className="loan-info-row">
                <span className="loan-info-label">
                  Возвраты на подтверждении
                </span>

                <span className="loan-info-value">
                  {formatMoney(
                    loan.pending_repayments_total || 0,
                    currency,
                  )}

                  <p className="loan-overdue-text">
                    Количество возвратов: {pendingRepaymentsCount}
                  </p>
                </span>
              </div>
            )}
          </div>

          {isFundingPending && !isExpiredLoan && (
            <div className="loan-info-panel funding-confirmation-panel">
              <h3 className="loan-info-title">
                Подтверждение фактической передачи
              </h3>

              {(isLender || isAdmin) && (
                <div className="funding-confirmation-section">
                  <p className="funding-confirmation-title">
                    Готовность кредитора зафиксирована.
                  </p>

                  <p className="muted">
                    Приложение ожидает, когда заемщик подтвердит фактическое
                    получение денежных средств вне приложения.
                  </p>

                  <p className="legal-confirmation-text">
                    Сервис фиксирует действия сторон и технические события.
                    Передача денежных средств происходит вне приложения.
                  </p>

                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() =>
                      setEnhancedConfirmationVisible((currentValue) =>
                        !currentValue
                      )
                    }
                  >
                    {enhancedConfirmationVisible
                      ? "Скрыть усиленное подтверждение"
                      : "Усиленное подтверждение кодом"}
                  </button>

                  {enhancedConfirmationVisible && (
                    <>
                      {fundingActivationCode ? (
                        <div className="activation-code-box">
                          <span>Код подтверждения</span>
                          <strong>{fundingActivationCode}</strong>
                        </div>
                      ) : (
                        <p className="muted">
                          Ранее созданный код повторно не отображается.
                          При необходимости можно сгенерировать новый код.
                        </p>
                      )}
                    </>
                  )}

                  {enhancedConfirmationVisible && canRegenerateActivationCode && (
                    <button
                      type="button"
                      className="secondary-button"
                      disabled={regenerateProcessing}
                      onClick={handleRegenerateActivationCode}
                    >
                      {regenerateProcessing
                        ? "Генерируем..."
                        : "Сгенерировать новый код"}
                    </button>
                  )}
                </div>
              )}

              {(isBorrower || isAdmin) && (
                <div className="funding-confirmation-section">
                  <p className="funding-confirmation-title">
                    Кредитор подтвердил готовность передать средства.
                  </p>

                  <p className="muted">
                    Нажмите кнопку только после фактического получения денежных
                    средств вне приложения.
                  </p>

                  <p className="legal-confirmation-text">
                    Я подтверждаю, что фактическое получение денежных средств
                    от кредитора произошло вне приложения, и прошу зафиксировать
                    это действие в карточке займа.
                  </p>

                  {activationActionError && (
                    <p className="form-error">
                      {activationActionError}
                    </p>
                  )}

                  {activationActionSuccess && (
                    <p className="form-success">
                      {activationActionSuccess}
                    </p>
                  )}

                  {canActivateLoan && (
                    <button
                      type="button"
                      disabled={activationProcessing}
                      onClick={handleActivateLoanByConfirmation}
                    >
                      {activationProcessing
                        ? "Подтверждаем..."
                        : "Подтвердить фактическое получение"}
                    </button>
                  )}

                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() =>
                      setEnhancedConfirmationVisible((currentValue) =>
                        !currentValue
                      )
                    }
                  >
                    {enhancedConfirmationVisible
                      ? "Скрыть ввод кода"
                      : "Подтвердить по коду"}
                  </button>

                  {enhancedConfirmationVisible && (
                    <>
                      <label className="form-field">
                        <span>4-значный код</span>

                        <input
                          type="text"
                          inputMode="numeric"
                          autoComplete="one-time-code"
                          value={activationCodeInput}
                          onChange={handleActivationCodeInputChange}
                          placeholder="0000"
                        />
                      </label>

                      <p className="muted">
                        Кодовый вариант нужен только для усиленного сценария,
                        когда стороны хотят дополнительно сверить действие.
                      </p>

                      {canActivateLoan && (
                        <button
                          type="button"
                          className="secondary-button"
                          disabled={activationProcessing}
                          onClick={handleActivateLoan}
                        >
                          {activationProcessing
                            ? "Проверяем код..."
                            : "Подтвердить по коду"}
                        </button>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          )}

          {hasPendingRepayments && (
            <div className="loan-info-panel">
              <h3 className="loan-info-title">
                Возвраты на подтверждении
              </h3>

              {repaymentActionError && (
                <p className="form-error">
                  {repaymentActionError}
                </p>
              )}

              {pendingRepayments.length === 0 && (
                <p className="muted">
                  Откройте историю возвратов, чтобы посмотреть детали.
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
                    className="repayment-item"
                    key={repayment.id}
                  >
                    <p>
                      <strong>
                        Сумма:
                      </strong>{" "}
                      {formatMoney(
                        repayment.amount,
                        currency,
                      )}
                    </p>

                    <p>
                      <strong>
                        Дата:
                      </strong>{" "}
                      {formatDate(repayment.created_at)}
                    </p>

                    {showBorrowerNotice && (
                      <p className="muted">
                        Возврат ожидает подтверждения кредитором.
                      </p>
                    )}

                    {canManage && (
                      <div className="actions">
                        <button
                          type="button"
                          disabled={isProcessing}
                          onClick={() =>
                            handleConfirmPendingRepayment(repayment.id)
                          }
                        >
                          {isProcessing
                            ? "Обработка..."
                            : "Подтвердить получение суммы"}
                        </button>

                        <button
                          type="button"
                          className="danger-button"
                          disabled={isProcessing}
                          onClick={() =>
                            handleRejectPendingRepayment(repayment.id)
                          }
                        >
                          Отклонить возврат
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
              <strong>
                Заемщик:
              </strong>{" "}
              {borrowerName}
            </p>

            <p>
              <strong>
                Кредитор:
              </strong>{" "}
              {lenderName}
            </p>

            <p>
              <strong>
                Валюта:
              </strong>{" "}
              {currency}
            </p>

            <p>
              <strong>
                Описание:
              </strong>{" "}
              {loan.description || "Без описания"}
            </p>
          </div>

          {canConfirmOrReject && (
            <div className="actions">
              <button
                type="button"
                onClick={() => onConfirm(loan.id)}
              >
                Готов передать вне приложения
              </button>

              <button
                type="button"
                className="danger-button"
                onClick={() => onReject(loan.id)}
              >
                Отклонить
              </button>
            </div>
          )}

          {canRepay && (
            <div className="repay-box">
              <RepayForm
                currency={currency}
                onRepay={(amount) => onRepay(loan.id, amount)}
              />
            </div>
          )}

          <div className="loan-actions-stack">
            {canMarkPaid && (
              <button
                type="button"
                onClick={handleMarkPaid}
              >
                {markPaidButtonText}
              </button>
            )}

            <button
              type="button"
              className="secondary-button"
              onClick={handleToggleHistory}
            >
              {historyVisible
                ? "Скрыть историю возвратов"
                : "Показать историю возвратов"}
            </button>

            <button
              type="button"
              className="secondary-button"
              onClick={handleToggleInterestLedger}
            >
              {interestLedgerVisible
                ? "Скрыть историю процентов"
                : "Показать историю процентов"}
            </button>
          </div>

          {historyLoading && (
            <p className="muted">
              Загружаем историю...
            </p>
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
            <p className="muted">
              Загружаем историю процентов...
            </p>
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
        </>
      )}
    </article>
  );
}

export default LoanCard;
