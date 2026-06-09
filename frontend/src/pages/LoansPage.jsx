import { useMemo, useState } from "react";

import EmptyState from "../components/EmptyState";
import HeaderStats from "../components/HeaderStats";
import LoanCard from "../components/LoanCard";
import LoanFilters from "../components/LoanFilters";

function LoansPage({
  loans,
  user,
  isAdmin,
  repayments,
  onConfirm,
  onReject,
  onMarkPaid,
  onRepay,
}) {
  const [filter, setFilter] = useState("all");

  const filteredLoans = useMemo(() => {
    const sorted = [...loans].sort((a, b) => b.id - a.id);

    if (filter === "all") {
      return sorted;
    }

    return sorted.filter((loan) => loan.status === filter);
  }, [loans, filter]);

  return (
    <div>
      <HeaderStats loans={loans} />

      <LoanFilters
        value={filter}
        onChange={setFilter}
      />

      <h2 className="page-title">
        {isAdmin ? "All Loans" : "Loans"}
      </h2>

      {filteredLoans.length === 0 && (
        <EmptyState
          title="No loans found"
          text="There are no loans for the selected filter."
        />
      )}

      {filteredLoans.map((loan) => (
        <LoanCard
          key={loan.id}
          loan={loan}
          user={user}
          isAdmin={isAdmin}
          repayments={repayments[loan.id] || []}
          onConfirm={onConfirm}
          onReject={onReject}
          onMarkPaid={onMarkPaid}
          onRepay={onRepay}
        />
      ))}
    </div>
  );
}

export default LoansPage;