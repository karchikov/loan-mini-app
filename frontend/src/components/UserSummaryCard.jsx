import { formatMoney } from "../utils/formatters";

function UserSummaryCard({
  summary,
}) {
  if (!summary) {
    return null;
  }

  return (
    <div className="card">
      <h2 className="page-title">
        User Card
      </h2>

      <p>
        <strong>Мои долги:</strong>{" "}
        {formatMoney(summary.my_debts)}
      </p>

      <p>
        <strong>Мне должны:</strong>{" "}
        {formatMoney(summary.owed_to_me)}
      </p>

      <p>
        <strong>Баланс:</strong>{" "}
        {formatMoney(summary.balance)}
      </p>

      <p>
        <strong>Активных займов:</strong>{" "}
        {summary.active_loans_count}
      </p>
    </div>
  );
}

export default UserSummaryCard;