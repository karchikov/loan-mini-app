import { NavLink } from "react-router-dom";

function MainLayout({
  children,
  user,
  onLogout,
}) {
  return (
    <div className="app">
      <div className="topbar">
        <div>
          <h1 className="app-title">
            Займы
          </h1>

          {user && (
            <p className="app-subtitle">
              @{user.username}
            </p>
          )}
        </div>

        {user && (
          <button
            className="logout-button"
            onClick={onLogout}
          >
            Выйти
          </button>
        )}
      </div>

      {user && (
        <div className="tabs">
          <NavLink
            to="/"
            className={({ isActive }) =>
              isActive
                ? "tab-button active"
                : "tab-button"
            }
          >
            Займы
          </NavLink>
        </div>
      )}

      {children}
    </div>
  );
}

export default MainLayout;