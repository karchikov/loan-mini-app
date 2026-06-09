import client from "./client";

export async function getUserSummary() {
  const response = await client.get(
    "/users/me/summary"
  );

  return response.data;
}

export async function getUserHistory() {
  const response = await client.get(
    "/users/me/history"
  );

  return response.data;
}