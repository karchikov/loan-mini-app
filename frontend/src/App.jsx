import { useCallback, useEffect, useState } from "react";

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
    reject,
    markPaid,
    repay,
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

  const reloadDashboard = useCallback(async () => {
    const dashboard = await loadDashboard();

    applyDashboardData(dashboard);

    return dashboard;
  }, []);

  async function handleCreate(loanData) {
    await create(loanData);
    await reloadDashboard();
  }

  async function handleConfirm(loanId) {
    await confirm(loanId);
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

  function handleLogout() {
    logout();
    clearLoans();
    setAvailableLenders([]);
    setSummary(null);
    setHistory([]);
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

        await reloadDashboard();
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
  }, [
    login,
    reloadDashboard,
  ]);

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
                  onLoadRepayments={loadRepayments}
                  onConfirm={handleConfirm}
                  onReject={handleReject}
                  onMarkPaid={handleMarkPaid}
                  onRepay={handleRepay}
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
                onLoadRepayments={loadRepayments}
                onConfirm={handleConfirm}
                onReject={handleReject}
                onMarkPaid={handleMarkPaid}
                onRepay={handleRepay}
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