import client from "./client";

export async function createLoan(data) {
  const response = await client.post("/loans", data);

  return response.data;
}