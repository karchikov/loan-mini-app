function LoanFilters({ value, onChange }) {
  const filters = [
    { value: "all", label: "All" },
    { value: "draft", label: "Draft" },
    { value: "active", label: "Active" },
    { value: "partially_paid", label: "Partial" },
    { value: "paid", label: "Paid" },
    { value: "rejected", label: "Rejected" },
  ];

  return (
    <div className="filters">
      {filters.map((filter) => (
        <button
          key={filter.value}
          className={
            value === filter.value
              ? "filter-button active"
              : "filter-button"
          }
          onClick={() => onChange(filter.value)}
        >
          {filter.label}
        </button>
      ))}
    </div>
  );
}

export default LoanFilters;