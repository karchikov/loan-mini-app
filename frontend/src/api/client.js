import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL;

const client = axios.create({
  baseURL: API_BASE_URL,
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API ERROR:", error);

    if (error.response?.status === 401) {
      localStorage.removeItem("token");

      window.location.reload();
    }

    return Promise.reject(error);
  }
);

export default client;