import { useState } from "react";

import { createLoan } from "../api/createLoan";

import {
  activateLoan,
  confirmLoan,
  confirmRepayment,
  getRepayments,
  markLoanPaid,
  regenerateFundingActivationCode,
  rejectLoan,
  rejectRepayment,
  repayLoan,
} from "../api/loans";

export function useLoans() {
  const [loans, setLoans] = useState([]);
  const [repayments, setRepayments] = useState({});

  async function loadRepayments(loanId, force = false) {
    if (!force && repayments[loanId]) {
      return repayments[loanId];
    }

    const history = await getRepayments(loanId);

    setRepayments((current) => ({
      ...current,
      [loanId]: history,
    }));

    return history;
  }

  async function create(data) {
    await createLoan(data);
  }

  async function confirm(id) {
    return confirmLoan(id);
  }

  async function regenerateActivationCode(id) {
    return regenerateFundingActivationCode(id);
  }

  async function activate(id, activationCode) {
    return activateLoan(id, activationCode);
  }

  async function reject(id) {
    await rejectLoan(id);
  }

  async function markPaid(id) {
    await markLoanPaid(id);
  }

  async function repay(id, amount) {
    await repayLoan(id, amount);
  }

  async function confirmPayment(loanId, repaymentId) {
    await confirmRepayment(loanId, repaymentId);
  }

  async function rejectPayment(loanId, repaymentId) {
    await rejectRepayment(loanId, repaymentId);
  }

  function clearLoans() {
    setLoans([]);
    setRepayments({});
  }

  return {
    loans,
    setLoans,
    repayments,
    loadRepayments,
    create,
    confirm,
    regenerateActivationCode,
    activate,
    reject,
    markPaid,
    repay,
    confirmPayment,
    rejectPayment,
    clearLoans,
  };
}