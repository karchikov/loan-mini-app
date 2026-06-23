import client from "./client";

export async function getLoans() {
  const response = await client.get("/loans");

  return response.data;
}

export async function confirmLoan(loanId) {
  const response = await client.post(`/loans/${loanId}/confirm`);

  return response.data;
}

export async function rejectLoan(loanId) {
  const response = await client.post(`/loans/${loanId}/reject`);

  return response.data;
}

export async function markLoanPaid(loanId) {
  const response = await client.post(`/loans/${loanId}/mark-paid`);

  return response.data;
}

export async function repayLoan(loanId, amount) {
  const response = await client.post(`/loans/${loanId}/repay`, {
    amount,
  });

  return response.data;
}

export async function confirmRepayment(loanId, repaymentId) {
  const response = await client.post(
    `/loans/${loanId}/repayments/${repaymentId}/confirm`
  );

  return response.data;
}

export async function rejectRepayment(loanId, repaymentId) {
  const response = await client.post(
    `/loans/${loanId}/repayments/${repaymentId}/reject`
  );

  return response.data;
}

export async function getRepayments(loanId) {
  const response = await client.get(`/loans/${loanId}/repayments`);

  return response.data;
}

export async function getInterestLedger(loanId) {
  const response = await client.get(`/loans/${loanId}/interest-ledger`);

  return response.data;
}