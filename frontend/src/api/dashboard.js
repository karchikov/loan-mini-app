import client from "./client";

export async function loadDashboard() {
  const response = await client.get(
    "/dashboard"
  );

  return response.data;
}