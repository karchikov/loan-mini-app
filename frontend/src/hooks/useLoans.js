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

import { loanStore } from "../store/loanStore";

export function useLoans() {
  const [loans, setLoans] = useState([]);
  const [repayments, setRepayments] = useState({});

  async function loadLoans() {
    try {
      const loanList = await getLoans();

      setLoans(loanList);

      const repaymentResults = await Promise.all(
        loanList.map(async (loan) => {
          const history = await getRepayments(loan.id);

          return {
            loanId: loan.id,
            history,
          };
        })
      );

      const repaymentMap = {};

      for (const item of repaymentResults) {
        repaymentMap[item.loanId] = item.history;
      }

      setRepayments(
        loanStore.normalizeRepayments(
          loanList,
          repaymentMap
        )
      );
    } catch (error) {
      console.error(error);
    }
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
  }

  function clearLoans() {
    setLoans([]);
    setRepayments({});
  }

  return {
    loans,
    repayments,
    loadLoans,
    create,
    confirm,
    reject,
    markPaid,
    repay,
    clearLoans,
  };
}