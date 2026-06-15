import { useState } from "react";

import { createLoan } from "../api/createLoan";

import {
  confirmLoan,
  getLoans,
  getRepayments,
  markLoanPaid,
  rejectLoan,
  repayLoan,
} from "../api/loans";

export function useLoans() {
  const [loans, setLoans] = useState([]);
  const [repayments, setRepayments] = useState({});

  async function loadLoans() {
    try {
      const loanList = await getLoans();

      setLoans(loanList);
    } catch (error) {
      console.error(error);
    }
  }

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
    await loadLoans();
  }

  async function confirm(id) {
    await confirmLoan(id);
    await loadLoans();
  }

  async function reject(id) {
    await rejectLoan(id);
    await loadLoans();
  }

  async function markPaid(id) {
    await markLoanPaid(id);
    await loadLoans();
  }

  async function repay(id, amount) {
    await repayLoan(id, amount);
    await loadLoans();
    await loadRepayments(id, true);
  }

  function clearLoans() {
    setLoans([]);
    setRepayments({});
  }

  return {
    loans,
    repayments,
    loadLoans,
    loadRepayments,
    create,
    confirm,
    reject,
    markPaid,
    repay,
    clearLoans,
  };
}