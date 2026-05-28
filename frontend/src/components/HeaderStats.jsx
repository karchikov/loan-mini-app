function HeaderStats({ loans }) {
  const total = loans.length;

  const active = loans.filter(
    (loan) =>
      loan.status === "active" ||
      loan.status === "partially_paid"
  ).length;

  const paid = loans.filter(
    (loan) => loan.status === "paid"
  ).length;

  return (
    <div className="stats-grid">
      <div className="stat-card">
        <span>Total</span>
        <strong>{total}</strong>
      </div>

      <div className="stat-card">
        <span>Active</span>
        <strong>{active}</strong>
      </div>

      <div className="stat-card">
        <span>Paid</span>
        <strong>{paid}</strong>
      </div>
    </div>
  );
}

export default HeaderStats;