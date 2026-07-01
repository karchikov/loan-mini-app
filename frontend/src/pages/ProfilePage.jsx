import { formatMoney } from "../utils/formatters";

function getDisplayName(user) {
  if (!user) {
    return "Пользователь";
  }

  return user.first_name || user.username || `Пользователь #${user.id}`;
}

function getInitials(user) {
  const name = getDisplayName(user);

  return name
    .split(" ")
    .map((part) => part[0])
    .filter(Boolean)
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function ProfilePage({
  user,
  summary,
  lenders,
  onLogout,
}) {
  return (
    <div className="profile-page">
      <section className="profile-card">
        <div className="profile-avatar">
          {getInitials(user)}
        </div>

        <h2>
          {getDisplayName(user)}
        </h2>

        <p>
          {user?.username ? `@${user.username}` : "Telegram Mini App"}
          {user?.role === "admin" ? " · администратор" : ""}
        </p>

        <div className="profile-stats">
          <div className="profile-stat">
            <span>Активных займов</span>
            <strong>{summary?.active_loans_count || 0}</strong>
          </div>

          <div className="profile-stat">
            <span>Контактов в сети</span>
            <strong>{lenders.length}</strong>
          </div>

          <div className="profile-stat">
            <span>Мне должны</span>
            <strong>{formatMoney(summary?.owed_to_me || 0)}</strong>
          </div>

          <div className="profile-stat">
            <span>Мои долги</span>
            <strong>{formatMoney(summary?.my_debts || 0)}</strong>
          </div>
        </div>
      </section>

      <button
        type="button"
        className="logout-button profile-logout-button"
        onClick={onLogout}
      >
        Выйти
      </button>
    </div>
  );
}

export default ProfilePage;
