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
            Loan Mini App
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
            Logout
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
            Loans
          </NavLink>
        </div>
      )}

      {children}
    </div>
  );
}

export default MainLayout;