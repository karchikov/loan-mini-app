import client from "./client";

export async function getUserSummary() {
  const response = await client.get(
    "/users/me/summary"
  );

  return response.data;
}