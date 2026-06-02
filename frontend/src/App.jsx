import { useEffect, useState } from "react";

import {
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import MainLayout from "./layouts/MainLayout";

import LoansPage from "./pages/LoansPage";

import CreateLoanForm from "./components/CreateLoanForm";
import LoadingScreen from "./components/LoadingScreen";

import { getUsers } from "./api/users";

import { useAuth } from "./hooks/useAuth";
import { useLoans } from "./hooks/useLoans";

import { authStore } from "./store/authStore";
import { initTelegram } from "./utils/telegram";

function App() {
  const [appLoading, setAppLoading] = useState(true);
  const [globalError, setGlobalError] = useState("");
  const [users, setUsers] = useState([]);

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

  async function loadUsers() {
    const usersList = await getUsers();

    setUsers(usersList);
  }

  async function bootstrap() {
    try {
      setGlobalError("");

      await loadProfile();
      await loadLoans();
      await loadUsers();
    } catch (error) {
      console.error(error);

      setGlobalError("Failed to load application data");
    } finally {
      setAppLoading(false);
    }
  }

  function handleLogout() {
    logout();
    clearLoans();
    setUsers([]);
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
            "Open this app from Telegram"
          );

          return;
        }

        const profile = await login();

        if (profile) {
          await loadLoans();
          await loadUsers();
        }
      } catch (error) {
        console.error(error);

        setGlobalError(
          "Telegram login failed"
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
                <CreateLoanForm
                  users={users}
                  onCreate={create}
                />

                <LoansPage
                  loans={loans}
                  user={user}
                  repayments={repayments}
                  onConfirm={confirm}
                  onReject={reject}
                  onMarkPaid={markPaid}
                  onRepay={repay}
                />
              </>
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