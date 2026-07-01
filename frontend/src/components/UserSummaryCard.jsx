import { formatMoney } from "../utils/formatters";

function UserSummaryCard({
  summary,
}) {
  if (!summary) {
    return null;
  }

  return (
    <section className="home-hero">
      <h1>
        Учет личных договоренностей
      </h1>

      <p>
        Приложение фиксирует заявки и действия сторон.
        Деньги передаются вне приложения.
      </p>

      <div className="home-summary-grid">
        <div className="home-summary-box">
          <span>Мне должны</span>
          <strong>{formatMoney(summary.owed_to_me)}</strong>
        </div>

        <div className="home-summary-box">
          <span>Мои долги</span>
          <strong>{formatMoney(summary.my_debts)}</strong>
        </div>
      </div>
    </section>
  );
}

export default UserSummaryCard;
