import { useEffect, useRef, useState } from "react";

import {
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import MainLayout from "./layouts/MainLayout";

import HistoryPage from "./pages/HistoryPage";
import LoansPage from "./pages/LoansPage";

import CreateLoanForm from "./components/CreateLoanForm";
import InviteUserButton from "./components/InviteUserButton";
import LoadingScreen from "./components/LoadingScreen";
import UserSummaryCard from "./components/UserSummaryCard";

import { loadDashboard } from "./api/dashboard";

import { useAuth } from "./hooks/useAuth";
import { useLoans } from "./hooks/useLoans";

import { authStore } from "./store/authStore";
import { initTelegram } from "./utils/telegram";

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

  function pushNotification(message, type = "info") {
    const id = `${Date.now()}-${Math.random()}`;

    setNotifications((current) => [
      ...current,
      {
        id,
        message,
        type,
      },
    ]);

    window.setTimeout(() => {
      setNotifications((current) =>
        current.filter((item) => item.id !== id)
      );
    }, 5000);
  }

  function getLoanSnapshot(loan) {
    return {
      status: loan.status,
      pendingRepaymentsCount: Number(
        loan.pending_repayments_count || 0
      ),
    };
  }

  function getStatusNotification(loan) {
    if (loan.status === "funding_pending") {
      return "Кредитор подтвердил готовность. Ожидается подтверждение заемщика.";
    }

    if (loan.status === "active") {
      return "Займ активирован. Подтверждение сторон зафиксировано.";
    }

    if (loan.status === "rejected") {
      return "Заявка по займу отклонена.";
    }

    if (loan.status === "paid") {
      return "Займ закрыт.";
    }

    if (loan.status === "expired") {
      return "Срок заявки истек.";
    }

    return "";
  }

  function syncDashboardNotifications(nextLoans) {
    const nextSnapshots = new Map();

    nextLoans.forEach((loan) => {
      const previousSnapshot = previousLoanSnapshotsRef.current.get(loan.id);
      const nextSnapshot = getLoanSnapshot(loan);

      nextSnapshots.set(loan.id, nextSnapshot);

      if (!dashboardInitializedRef.current || !previousSnapshot) {
        return;
      }

      if (previousSnapshot.status !== nextSnapshot.status) {
        const message = getStatusNotification(loan);

        if (message) {
          pushNotification(message);
        }
      }

      if (
        nextSnapshot.pendingRepaymentsCount >
        previousSnapshot.pendingRepaymentsCount
      ) {
        pushNotification(
          "Есть платеж, ожидающий подтверждения.",
        );
      }
    });

    previousLoanSnapshotsRef.current = nextSnapshots;
    dashboardInitializedRef.current = true;
  }

  function applyDashboardData(dashboard) {
    const dashboardUser = dashboard.user || null;
    const dashboardLoans = dashboard.loans || [];

    setUser(dashboardUser);
    setLoans(dashboardLoans);
    setSummary(dashboard.summary || null);
    setHistory(dashboard.history || []);
    syncDashboardNotifications(dashboardLoans);

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
    setNotifications([]);
    dashboardInitializedRef.current = false;
    previousLoanSnapshotsRef.current = new Map();
  }

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
      onLogout={handleLogout}
    >
      {globalError && (
        <div className="global-error">
          {globalError}
        </div>
      )}

      {notifications.length > 0 && (
        <div className="notification-stack">
          {notifications.map((notification) => (
            <div
              className={`app-notification ${notification.type}`}
              key={notification.id}
            >
              {notification.message}
            </div>
          ))}
        </div>
      )}

      {user && (
        <Routes>
          <Route
            path="/"
            element={
              <>
                <UserSummaryCard
                  summary={summary}
                />

                <InviteUserButton
                  onInviteSent={reloadDashboard}
                />

                <CreateLoanForm
                  lenders={availableLenders}
                  onCreate={handleCreate}
                  onInviteSent={reloadDashboard}
                />

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
              </>
            }
          />

          <Route
            path="/paid"
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
            path="/history"
            element={
              <HistoryPage history={history} />
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
