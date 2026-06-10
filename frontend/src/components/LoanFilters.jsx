function LoanFilters({ value, onChange }) {
  const filters = [
    { value: "all", label: "Все" },
    { value: "draft", label: "Ожидают" },
    { value: "active", label: "Активные" },
    { value: "partially_paid", label: "Частично погашены" },
    { value: "paid", label: "Погашены" },
    { value: "rejected", label: "Отклонены" },
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