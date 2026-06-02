import client from "./client";

export async function getUsers() {
  const response = await client.get(
    "/users"
  );

  return response.data;
}