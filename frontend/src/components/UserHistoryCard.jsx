import { formatDate, formatMoney } from "../utils/formatters";

function UserHistoryCard({
  title = "Последние события",
  emptyText = "Событий пока нет",
  history,
}) {
  if (!history) {
    return null;
  }

  return (
    <div className="card">
      <h2 className="page-title">
        {title}
      </h2>

      {history.length === 0 && (
        <p className="muted">
          {emptyText}
        </p>
      )}

      {history.map((item) => (
        <div
          key={item.id}
          className="repayment-item"
        >
          <p>
            <strong>{item.title}</strong>
          </p>

          <p>
            {item.description}
          </p>

          {item.amount !== null && (
            <p>
              <strong>Сумма:</strong>{" "}
              {formatMoney(item.amount)}
            </p>
          )}

          <p>
            <strong>Дата:</strong>{" "}
            {formatDate(item.created_at)}
          </p>
        </div>
      ))}
    </div>
  );
}

export default UserHistoryCard;
