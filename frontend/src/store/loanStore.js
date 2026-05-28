export const loanStore = {
  normalizeRepayments(loans, repaymentsMap) {
    const result = {};

    for (const loan of loans) {
      result[loan.id] =
        repaymentsMap[loan.id] || [];
    }

    return result;
  },
};