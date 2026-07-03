import client from "./client";

export async function getUsers() {
  const response = await client.get(
    "/users"
  );

  return response.data;
}

export async function getAvailableLenders() {
  const response = await client.get(
    "/users/me/available-lenders"
  );

  return response.data;
}

export async function getMyInviteLink() {
  const response = await client.get(
    "/users/me/invite"
  );

  return response.data;
}

export async function updateContactAlias(
  contactUserId,
  alias,
) {
  const response = await client.put(
    `/users/me/contact-aliases/${contactUserId}`,
    {
      alias,
    },
  );

  return response.data;
}
