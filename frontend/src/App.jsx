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

import { useAuth } from "./hooks/useAuth";
import { useLoans } from "./hooks/useLoans";

import { authStore } from "./store/authStore";
import { initTelegram } from "./utils/telegram";

function App() {
  const [appLoading, setAppLoading] = useState(true);
  const [globalError, setGlobalError] = useState("");

  const {
    user,
    loading,
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

  async function bootstrap() {
    try {
      setGlobalError("");

      await loadProfile();
      await loadLoans();
    } catch (error) {
      console.error(error);

      setGlobalError("Failed to load application data");
    } finally {
      setAppLoading(false);
    }
  }

  async function handleLogin(devUser) {
    try {
      setGlobalError("");

      const profile = await login(devUser);

      if (profile) {
        await loadLoans();
      }
    } catch (error) {
      console.error(error);

      setGlobalError("Login failed");
    }
  }

  function handleLogout() {
    logout();
    clearLoans();
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

        if (tg?.initData) {
          const profile =
            await login();

          if (profile) {
            await loadLoans();
          }
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

  const isTelegram =
    !!window.Telegram?.WebApp?.initData;

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

      {!user && !isTelegram && (
        <div className="card">
          <button
            className="full-width"
            onClick={() => handleLogin("roman")}
            disabled={loading}
            style={{
              marginBottom: "10px",
            }}
          >
            {loading
              ? "Loading..."
              : "Login Roman"}
          </button>

          <button
            className="full-width"
            onClick={() => handleLogin("sixx")}
            disabled={loading}
          >
            {loading
              ? "Loading..."
              : "Login Sixx"}
          </button>
        </div>
      )}

      {user && (
        <Routes>
          <Route
            path="/"
            element={
              <>
                <CreateLoanForm
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