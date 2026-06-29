import { useEffect, useState } from "react";

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
    reject,
    markPaid,
    repay,
    confirmPayment,
    rejectPayment,
    clearLoans,
  } = useLoans();

  const isAdmin = user?.role === "admin";

  function applyDashboardData(dashboard) {
    const dashboardUser = dashboard.user || null;

    setUser(dashboardUser);
    setLoans(dashboard.loans || []);
    setSummary(dashboard.summary || null);
    setHistory(dashboard.history || []);

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