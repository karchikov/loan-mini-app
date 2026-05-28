import client from "./client";

export async function devLogin(data) {
  const response = await client.post(
    "/auth/dev-login",
    null,
    {
      params: data,
    }
  );

  return response.data;
}

export async function telegramLogin(
  initData
) {
  const response = await client.post(
    "/auth/telegram",
    null,
    {
      params: {
        init_data: initData,
      },
    }
  );

  return response.data;
}

export async function getMe() {
  const response = await client.get(
    "/me"
  );

  return response.data;
}