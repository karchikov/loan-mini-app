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
import LoadingScreen from "./components/LoadingScreen";
import UserSummaryCard from "./components/UserSummaryCard";

import {
  getUserHistory,
  getUserSummary,
} from "./api/summary";
import { getUsers } from "./api/users";

import { useAuth } from "./hooks/useAuth";
import { useLoans } from "./hooks/useLoans";

import { authStore } from "./store/authStore";
import { initTelegram } from "./utils/telegram";

function App() {
  const [appLoading, setAppLoading] = useState(true);
  const [globalError, setGlobalError] = useState("");
  const [users, setUsers] = useState([]);
  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState(null);

  const {
    user,
    login,
    logout,
    loadProfile,
  } = useAuth();

  const {
    loans,
    repayments,
    loadLoans,
    create,
    confirm,
    reject,
    markPaid,
    repay,
    clearLoans,
  } = useLoans();

  const isAdmin = user?.role === "admin";

  async function loadUsers(currentUser) {
    if (!currentUser) {
      setUsers([]);
      return;
    }

    try {
      const usersList = await getUsers();

      if (currentUser.role === "admin") {
        setUsers(usersList);
        return;
      }

      setUsers(
        usersList.filter(
          (item) => item.id !== currentUser.id
        )
      );
    } catch (error) {
      console.error(error);

      setUsers([]);
    }
  }

  async function loadSummary() {
    try {
      const userSummary = await getUserSummary();

      setSummary(userSummary);
    } catch (error) {
      console.error(error);

      setSummary(null);
    }
  }

  async function loadHistory() {
    try {
      const userHistory = await getUserHistory();

      setHistory(userHistory);
    } catch (error) {
      console.error(error);

      setHistory(null);
    }
  }

  async function bootstrap() {
    try {
      setGlobalError("");

      const profile = await loadProfile();

      if (!profile) {
        setGlobalError(
          "Не удалось загрузить профиль пользователя"
        );

        return;
      }

      await loadLoans();
      await loadUsers(profile);
      await loadSummary();
      await loadHistory();
    } catch (error) {
      console.error(error);

      setGlobalError("Не удалось загрузить данные приложения");
    } finally {
      setAppLoading(false);
    }
  }

  async function refreshApplicationData(profile) {
    await loadLoans();
    await loadUsers(profile);
    await loadSummary();
    await loadHistory();
  }

  async function handleCreate(loanData) {
    await create(loanData);
    await loadSummary();
    await loadHistory();
  }

  async function handleConfirm(loanId) {
    await confirm(loanId);
    await loadSummary();
    await loadHistory();
  }

  async function handleReject(loanId) {
    await reject(loanId);
    await loadSummary();
    await loadHistory();
  }

  async function handleMarkPaid(loanId) {
    await markPaid(loanId);
    await loadSummary();
    await loadHistory();
  }

  async function handleRepay(loanId, amount) {
    await repay(loanId, amount);
    await loadSummary();
    await loadHistory();
  }

  function handleLogout() {
    logout();
    clearLoans();
    setUsers([]);
    setSummary(null);
    setHistory(null);
  }

  useEffect(() => {
    async function initialize() {
      try {
        initTelegram();

        const token = authStore.getToken();

        if (token) {
          await bootstrap();
          return;
        }

        const tg =
          window.Telegram?.WebApp;

        if (!tg?.initData) {
          setGlobalError(
            "Откройте приложение через Telegram"
          );

          return;
        }

        const profile = await login();

        if (profile) {
          await refreshApplicationData(profile);
        }
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

                <CreateLoanForm
                  users={users}
                  currentUser={user}
                  isAdmin={isAdmin}
                  onCreate={handleCreate}
                />

                <LoansPage
                  mode="active"
                  loans={loans}
                  user={user}
                  isAdmin={isAdmin}
                  repayments={repayments}
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