export const authStore = {
  getToken() {
    return localStorage.getItem("token");
  },

  setToken(token) {
    localStorage.setItem("token", token);
  },

  clear() {
    localStorage.removeItem("token");
  },
};