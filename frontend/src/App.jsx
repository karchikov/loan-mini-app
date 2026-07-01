import { useEffect, useRef, useState } from "react";

import {
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import MainLayout from "./layouts/MainLayout";

import HistoryPage from "./pages/HistoryPage";
import HomePage from "./pages/HomePage";
import LoansPage from "./pages/LoansPage";
import ProfilePage from "./pages/ProfilePage";

import LoadingScreen from "./components/LoadingScreen";

import { loadDashboard } from "./api/dashboard";

import { useAuth } from "./hooks/useAuth";
import { useLoans } from "./hooks/useLoans";

import { authStore } from "./store/authStore";
import { initTelegram } from "./utils/telegram";

const NOTIFICATION_TTL_MS = 6500;
const NOTIFICATION_DEDUPE_WINDOW_MS = 45000;
const MAX_VISIBLE_NOTIFICATIONS = 4;

function App() {
  const [appLoading, setAppLoading] = useState(true);
  const [globalError, setGlobalError] = useState("");
  const [availableLenders, setAvailableLenders] = useState([]);
  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState([]);
  const [fundingActivationCodes, setFundingActivationCodes] = useState({});
  const [notifications, setNotifications] = useState([]);
  const dashboardInitializedRef = useRef(false);
  const previousLoanSnapshotsRef = useRef(new Map());
  const notificationTimersRef = useRef(new Map());
  const recentNotificationKeysRef = useRef(new Map());

  const {
    user,
    setUser,
    login,
    logout,
  } = useAuth();

  const {
    loans,
    setLoans,
    repayments,
    loadRepayments,
    create,
    confirm,
    regenerateActivationCode,
    activate,
    activateByConfirmation,
    reject,
    markPaid,
    repay,
    confirmPayment,
    rejectPayment,
    clearLoans,
  } = useLoans();

  const isAdmin = user?.role === "admin";

  function dismissNotification(notificationId) {
    const timerId = notificationTimersRef.current.get(notificationId);

    if (timerId) {
      window.clearTimeout(timerId);
      notificationTimersRef.current.delete(notificationId);
    }

    setNotifications((current) =>
      current.filter((item) => item.id !== notificationId)
    );
  }

  function pushNotification(notification) {
    if (!notification?.message) {
      return;
    }

    const {
      key,
      message,
      type = "info",
    } = notification;

    const notificationKey = key || message;
    const nowMs = Date.now();
    const previousShownAt =
      recentNotificationKeysRef.current.get(notificationKey);

    if (
      previousShownAt &&
      nowMs - previousShownAt < NOTIFICATION_DEDUPE_WINDOW_MS
    ) {
      return;
    }

    recentNotificationKeysRef.current.set(notificationKey, nowMs);

    const id = `${Date.now()}-${Math.random()}`;
    const timerId = window.setTimeout(() => {
      dismissNotification(id);
    }, NOTIFICATION_TTL_MS);

    notificationTimersRef.current.set(id, timerId);

    setNotifications((current) => {
      const nextNotifications = [
        ...current,
        {
          id,
          message,
          type,
        },
      ];

      const visibleNotifications = nextNotifications.slice(
        -MAX_VISIBLE_NOTIFICATIONS,
      );
      const visibleNotificationIds = new Set(
        visibleNotifications.map((item) => item.id),
      );

      nextNotifications.forEach((item) => {
        if (visibleNotificationIds.has(item.id)) {
          return;
        }

        const removedTimerId = notificationTimersRef.current.get(item.id);

        if (removedTimerId) {
          window.clearTimeout(removedTimerId);
          notificationTimersRef.current.delete(item.id);
        }
      });

      return visibleNotifications;
    });
  }

  function getLoanCounterpartyName(loan, currentUser) {
    if (!loan || !currentUser) {
      return "";
    }

    if (loan.borrower_id === currentUser.id) {
      return loan.lender?.first_name || loan.lender?.username || "кредитор";
    }

    if (loan.lender_id === currentUser.id) {
      return loan.borrower?.first_name || loan.borrower?.username || "заемщик";
    }

    return "";
  }

  function getLoanUserRole(loan, currentUser) {
    if (!loan || !currentUser) {
      return "viewer";
    }

    if (currentUser.role === "admin") {
      return "admin";
    }

    if (loan.borrower_id === currentUser.id) {
      return "borrower";
    }

    if (loan.lender_id === currentUser.id) {
      return "lender";
    }

    return "viewer";
  }

  function buildStatusNotification(loan, currentUser) {
    const role = getLoanUserRole(loan, currentUser);
    const counterpartyName = getLoanCounterpartyName(loan, currentUser);
    const loanPrefix = `Займ №${loan.id}`;

    if (loan.status === "funding_pending") {
      if (role === "borrower") {
        return {
          key: `loan:${loan.id}:status:${loan.status}:borrower`,
          type: "warning",
          message:
            `${loanPrefix}: кредитор подтвердил готовность. ` +
            "После фактического получения средств подтвердите это в карточке.",
        };
      }

      if (role === "lender") {
        return {
          key: `loan:${loan.id}:status:${loan.status}:lender`,
          type: "info",
          message:
            `${loanPrefix}: ваша готовность зафиксирована. ` +
            "Ожидаем подтверждения заемщика.",
        };
      }

      return {
        key: `loan:${loan.id}:status:${loan.status}:admin`,
        type: "info",
        message:
          `${loanPrefix}: кредитор подтвердил готовность, ` +
          "ожидается подтверждение заемщика.",
      };
    }

    if (loan.status === "active") {
      if (role === "lender") {
        return {
          key: `loan:${loan.id}:status:${loan.status}:lender`,
          type: "success",
          message:
            `${loanPrefix}: заемщик подтвердил получение средств. ` +
            "Займ активирован.",
        };
      }

      if (role === "borrower") {
        return {
          key: `loan:${loan.id}:status:${loan.status}:borrower`,
          type: "success",
          message:
            `${loanPrefix}: получение средств зафиксировано. ` +
            "Займ активирован.",
        };
      }

      return {
        key: `loan:${loan.id}:status:${loan.status}:admin`,
        type: "success",
        message: `${loanPrefix}: займ активирован.`,
      };
    }

    if (loan.status === "waiting_confirmation") {
      return {
        key: `loan:${loan.id}:status:${loan.status}:${role}`,
        type: "warning",
        message:
          `${loanPrefix}: закрытие займа ожидает подтверждения кредитором.`,
      };
    }

    if (loan.status === "rejected") {
      return {
        key: `loan:${loan.id}:status:${loan.status}:${role}`,
        type: "error",
        message:
          role === "borrower"
            ? `${loanPrefix}: заявка отклонена кредитором.`
            : `${loanPrefix}: заявка отклонена.`,
      };
    }

    if (loan.status === "paid") {
      return {
        key: `loan:${loan.id}:status:${loan.status}:${role}`,
        type: "success",
        message:
          counterpartyName
            ? `${loanPrefix}: займ с ${counterpartyName} закрыт.`
            : `${loanPrefix}: займ закрыт.`,
      };
    }

    if (loan.status === "expired") {
      return {
        key: `loan:${loan.id}:status:${loan.status}:${role}`,
        type: "warning",
        message: `${loanPrefix}: срок заявки истек.`,
      };
    }

    return null;
  }

  function buildPendingRepaymentNotification(
    loan,
    currentUser,
    previousSnapshot,
    nextSnapshot,
  ) {
    if (
      nextSnapshot.pendingRepaymentsCount <=
      previousSnapshot.pendingRepaymentsCount
    ) {
      return null;
    }

    const role = getLoanUserRole(loan, currentUser);
    const loanPrefix = `Займ №${loan.id}`;

    if (role === "lender" || role === "admin") {
      return {
        key: `loan:${loan.id}:pending-repayment:${nextSnapshot.pendingRepaymentsCount}`,
        type: "warning",
        message:
          `${loanPrefix}: заемщик зафиксировал возврат на подтверждении. ` +
          "Проверьте карточку займа.",
      };
    }

    return {
      key: `loan:${loan.id}:pending-repayment:${nextSnapshot.pendingRepaymentsCount}`,
      type: "info",
      message:
        `${loanPrefix}: возврат ожидает подтверждения кредитором.`,
    };
  }

  function clearNotificationState(shouldClearVisibleNotifications = true) {
    notificationTimersRef.current.forEach((timerId) => {
      window.clearTimeout(timerId);
    });

    notificationTimersRef.current.clear();
    recentNotificationKeysRef.current.clear();

    if (shouldClearVisibleNotifications) {
      setNotifications([]);
    }
  }

  function getLoanSnapshot(loan) {
    return {
      status: loan.status,
      pendingRepaymentsCount: Number(
        loan.pending_repayments_count || 0
      ),
    };
  }

  function syncDashboardNotifications(nextLoans, currentUser) {
    const nextSnapshots = new Map();

    nextLoans.forEach((loan) => {
      const previousSnapshot = previousLoanSnapshotsRef.current.get(loan.id);
      const nextSnapshot = getLoanSnapshot(loan);

      nextSnapshots.set(loan.id, nextSnapshot);

      if (!dashboardInitializedRef.current || !previousSnapshot) {
        return;
      }

      if (previousSnapshot.status !== nextSnapshot.status) {
        pushNotification(
          buildStatusNotification(loan, currentUser),
        );
      }

      pushNotification(
        buildPendingRepaymentNotification(
          loan,
          currentUser,
          previousSnapshot,
          nextSnapshot,
        ),
      );
    });

    previousLoanSnapshotsRef.current = nextSnapshots;
    dashboardInitializedRef.current = true;
  }

  function pruneRecentNotificationKeys() {
    const nowMs = Date.now();

    recentNotificationKeysRef.current.forEach((shownAt, key) => {
      if (nowMs - shownAt > NOTIFICATION_DEDUPE_WINDOW_MS) {
        recentNotificationKeysRef.current.delete(key);
      }
    });
  }

  function applyDashboardData(dashboard) {
    const dashboardUser = dashboard.user || null;
    const dashboardLoans = dashboard.loans || [];

    setUser(dashboardUser);
    setLoans(dashboardLoans);
    setSummary(dashboard.summary || null);
    setHistory(dashboard.history || []);
    pruneRecentNotificationKeys();
    syncDashboardNotifications(dashboardLoans, dashboardUser);

    if (!dashboardUser) {
      setAvailableLenders([]);
      return;
    }

    setAvailableLenders(
      (dashboard.available_lenders || []).filter(
        (item) => item.id !== dashboardUser.id
      )
    );
  }

  async function reloadDashboard() {
    const dashboard = await loadDashboard();

    applyDashboardData(dashboard);

    return dashboard;
  }

  async function handleCreate(loanData) {
    await create(loanData);
    await reloadDashboard();
  }

  async function handleConfirm(loanId) {
    const result = await confirm(loanId);

    if (result?.activation_code) {
      setFundingActivationCodes((current) => ({
        ...current,
        [loanId]: result.activation_code,
      }));
    }

    await reloadDashboard();
  }

  async function handleRegenerateActivationCode(loanId) {
    const result = await regenerateActivationCode(loanId);

    if (result?.activation_code) {
      setFundingActivationCodes((current) => ({
        ...current,
        [loanId]: result.activation_code,
      }));
    }

    await reloadDashboard();
  }

  async function handleActivateLoan(loanId, activationCode) {
    await activate(loanId, activationCode);

    setFundingActivationCodes((current) => {
      const nextValue = {
        ...current,
      };

      delete nextValue[loanId];

      return nextValue;
    });

    await reloadDashboard();
  }

  async function handleActivateLoanByConfirmation(loanId) {
    await activateByConfirmation(loanId);

    setFundingActivationCodes((current) => {
      const nextValue = {
        ...current,
      };

      delete nextValue[loanId];

      return nextValue;
    });

    await reloadDashboard();
  }

  async function handleReject(loanId) {
    await reject(loanId);
    await reloadDashboard();
  }

  async function handleMarkPaid(loanId) {
    await markPaid(loanId);
    await reloadDashboard();
  }

  async function handleRepay(loanId, amount) {
    const shouldRefreshRepayments = Boolean(repayments[loanId]);

    await repay(loanId, amount);
    await reloadDashboard();

    if (shouldRefreshRepayments) {
      await loadRepayments(loanId, true);
    }
  }

  async function handleConfirmRepayment(loanId, repaymentId) {
    const shouldRefreshRepayments = Boolean(repayments[loanId]);

    await confirmPayment(loanId, repaymentId);
    await reloadDashboard();

    if (shouldRefreshRepayments) {
      await loadRepayments(loanId, true);
    }
  }

  async function handleRejectRepayment(loanId, repaymentId) {
    const shouldRefreshRepayments = Boolean(repayments[loanId]);

    await rejectPayment(loanId, repaymentId);
    await reloadDashboard();

    if (shouldRefreshRepayments) {
      await loadRepayments(loanId, true);
    }
  }

  function handleLogout() {
    logout();
    clearLoans();
    setAvailableLenders([]);
    setSummary(null);
    setHistory([]);
    setFundingActivationCodes({});
    clearNotificationState();
    dashboardInitializedRef.current = false;
    previousLoanSnapshotsRef.current = new Map();
  }

  useEffect(() => {
    return () => {
      clearNotificationState(false);
    };
  }, []);

  useEffect(() => {
    async function initialize() {
      try {
        setGlobalError("");

        initTelegram();

        const token = authStore.getToken();

        if (!token) {
          const tg =
            window.Telegram?.WebApp;

          if (!tg?.initData) {
            setGlobalError(
              "Откройте приложение через Telegram"
            );

            return;
          }

          const profile = await login();

          if (!profile) {
            setGlobalError(
              "Не удалось войти через Telegram"
            );

            return;
          }
        }

        const dashboard = await loadDashboard();

        applyDashboardData(dashboard);
      } catch (error) {
        console.error(error);

        setGlobalError(
          "Ошибка входа через Telegram"
        );
      } finally {
        setAppLoading(false);
      }
    }

    initialize();
  }, []);

  useEffect(() => {
    if (!user) {
      return undefined;
    }

    let refreshInProgress = false;

    async function refreshDashboardSafely() {
      if (refreshInProgress) {
        return;
      }

      try {
        refreshInProgress = true;

        await reloadDashboard();
      } catch (error) {
        console.error(error);
      } finally {
        refreshInProgress = false;
      }
    }

    function handleWindowFocus() {
      refreshDashboardSafely();
    }

    function handleVisibilityChange() {
      if (document.visibilityState === "visible") {
        refreshDashboardSafely();
      }
    }

    window.addEventListener(
      "focus",
      handleWindowFocus,
    );

    document.addEventListener(
      "visibilitychange",
      handleVisibilityChange,
    );

    const intervalId = window.setInterval(
      refreshDashboardSafely,
      15000,
    );

    return () => {
      window.removeEventListener(
        "focus",
        handleWindowFocus,
      );

      document.removeEventListener(
        "visibilitychange",
        handleVisibilityChange,
      );

      window.clearInterval(intervalId);
    };
  }, [user?.id]);

  if (appLoading) {
    return <LoadingScreen />;
  }

  return (
    <MainLayout
      user={user}
    >
      {globalError && (
        <div className="global-error">
          {globalError}
        </div>
      )}

      {notifications.length > 0 && (
        <div
          className="notification-stack"
          aria-live="polite"
        >
          {notifications.map((notification) => (
            <div
              className={`app-notification ${notification.type}`}
              key={notification.id}
            >
              <span>{notification.message}</span>

              <button
                type="button"
                className="notification-close-button"
                onClick={() => dismissNotification(notification.id)}
                aria-label="Закрыть уведомление"
              >
                x
              </button>
            </div>
          ))}
        </div>
      )}

      {user && (
        <Routes>
          <Route
            path="/"
            element={
              <HomePage
                summary={summary}
                lenders={availableLenders}
                loans={loans}
                user={user}
                isAdmin={isAdmin}
                repayments={repayments}
                fundingActivationCodes={fundingActivationCodes}
                onInviteSent={reloadDashboard}
                onCreate={handleCreate}
                onLoadRepayments={loadRepayments}
                onConfirm={handleConfirm}
                onRegenerateActivationCode={handleRegenerateActivationCode}
                onActivateLoan={handleActivateLoan}
                onActivateLoanByConfirmation={handleActivateLoanByConfirmation}
                onReject={handleReject}
                onMarkPaid={handleMarkPaid}
                onRepay={handleRepay}
                onConfirmRepayment={handleConfirmRepayment}
                onRejectRepayment={handleRejectRepayment}
              />
            }
          />

          <Route
            path="/profile"
            element={
              <ProfilePage
                user={user}
                summary={summary}
                lenders={availableLenders}
                onLogout={handleLogout}
              />
            }
          />

          <Route
            path="/events"
            element={
              <HistoryPage
                title="Последние события"
                emptyText="Событий пока нет"
                history={history}
              />
            }
          />

          <Route
            path="/active"
            element={
              <LoansPage
                mode="active"
                loans={loans}
                user={user}
                isAdmin={isAdmin}
                repayments={repayments}
                fundingActivationCodes={fundingActivationCodes}
                onLoadRepayments={loadRepayments}
                onConfirm={handleConfirm}
                onRegenerateActivationCode={handleRegenerateActivationCode}
                onActivateLoan={handleActivateLoan}
                onActivateLoanByConfirmation={handleActivateLoanByConfirmation}
                onReject={handleReject}
                onMarkPaid={handleMarkPaid}
                onRepay={handleRepay}
                onConfirmRepayment={handleConfirmRepayment}
                onRejectRepayment={handleRejectRepayment}
              />
            }
          />

          <Route
            path="/history"
            element={
              <LoansPage
                mode="paid"
                loans={loans}
                user={user}
                isAdmin={isAdmin}
                repayments={repayments}
                fundingActivationCodes={fundingActivationCodes}
                onLoadRepayments={loadRepayments}
                onConfirm={handleConfirm}
                onRegenerateActivationCode={handleRegenerateActivationCode}
                onActivateLoan={handleActivateLoan}
                onActivateLoanByConfirmation={handleActivateLoanByConfirmation}
                onReject={handleReject}
                onMarkPaid={handleMarkPaid}
                onRepay={handleRepay}
                onConfirmRepayment={handleConfirmRepayment}
                onRejectRepayment={handleRejectRepayment}
              />
            }
          />

          <Route
            path="/paid"
            element={
              <Navigate
                to="/history"
                replace
              />
            }
          />

          <Route
            path="/old-history"
            element={
              <Navigate
                to="/events"
                replace
              />
            }
          />

          <Route
            path="*"
            element={
              <Navigate
                to="/"
                replace
              />
            }
          />
        </Routes>
      )}
    </MainLayout>
  );
}

export default App;
