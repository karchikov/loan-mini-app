import { useState } from "react";

import { telegramLogin } from "../api/auth";

import { authStore } from "../store/authStore";

export function useAuth() {
  const [user, setUser] =
    useState(null);

  const [loading, setLoading] =
    useState(false);

  async function login() {
    try {
      setLoading(true);

      const tg =
        window.Telegram?.WebApp;

      if (!tg?.initData) {
        throw new Error(
          "Telegram initData not found"
        );
      }

      const data =
        await telegramLogin(
          tg.initData
        );

      authStore.setToken(
        data.access_token
      );

      return data;
    } catch (error) {
      console.error(error);

      return null;
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    authStore.clear();

    setUser(null);
  }

  return {
    user,
    setUser,
    loading,
    login,
    logout,
  };
}