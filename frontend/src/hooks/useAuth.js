import { useState } from "react";

import {
  devLogin,
  getMe,
  telegramLogin,
} from "../api/auth";

import { authStore } from "../store/authStore";

export function useAuth() {
  const [user, setUser] =
    useState(null);

  const [loading, setLoading] =
    useState(false);

  async function loadProfile() {
    try {
      const profile = await getMe();

      setUser(profile);

      return profile;
    } catch (error) {
      console.error(error);

      return null;
    }
  }

  async function login(devUser = "roman") {
    try {
      setLoading(true);

      const tg =
        window.Telegram?.WebApp;

      let data;

      if (tg?.initData) {
        data =
          await telegramLogin(
            tg.initData
          );
      } else {
        if (devUser === "sixx") {
          data = await devLogin({
            telegram_id: 654321,
            username: "sixx",
            first_name: "Sixx",
            last_name: "Borrower",
          });
        } else {
          data = await devLogin({
            telegram_id: 123456,
            username: "roman",
            first_name: "Roman",
            last_name: "Karchikov",
          });
        }
      }

      authStore.setToken(
        data.access_token
      );

      return await loadProfile();
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
    loadProfile,
  };
}