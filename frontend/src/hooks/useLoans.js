import { useState } from "react";

import { createLoan } from "../api/createLoan";

import {
  confirmLoan,
  getRepayments,
  markLoanPaid,
  rejectLoan,
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
    await confirmLoan(id);
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
    reject,
    markPaid,
    repay,
    clearLoans,
  };
}
