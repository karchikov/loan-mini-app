import client from "./client";

export async function getUsers() {
  const response = await client.get(
    "/users"
  );

  return response.data;
}

export async function getMyInviteLink() {
  const response = await client.get(
    "/users/me/invite"
  );

  return response.data;
}