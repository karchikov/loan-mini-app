import { NavLink } from "react-router-dom";

function MainLayout({
  children,
  user,
}) {
  return (
    <div className="app">
      <main className="app-content">
        {children}
      </main>

      {user && (
        <nav className="bottom-nav">
          <NavLink
            to="/profile"
            className={({ isActive }) =>
              isActive
                ? "bottom-nav-button active"
                : "bottom-nav-button"
            }
          >
            <span className="bottom-nav-icon">П</span>
            <span>Профиль</span>
          </NavLink>

          <NavLink
            to="/events"
            className={({ isActive }) =>
              isActive
                ? "bottom-nav-button active"
                : "bottom-nav-button"
            }
          >
            <span className="bottom-nav-icon">С</span>
            <span>События</span>
          </NavLink>

          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              isActive
                ? "bottom-nav-button home active"
                : "bottom-nav-button home"
            }
          >
            <span className="home-nav-icon">Г</span>
            <span>Главная</span>
          </NavLink>

          <NavLink
            to="/active"
            className={({ isActive }) =>
              isActive
                ? "bottom-nav-button active"
                : "bottom-nav-button"
            }
          >
            <span className="bottom-nav-icon">А</span>
            <span>Активные</span>
          </NavLink>

          <NavLink
            to="/history"
            className={({ isActive }) =>
              isActive
                ? "bottom-nav-button active"
                : "bottom-nav-button"
            }
          >
            <span className="bottom-nav-icon">И</span>
            <span>История</span>
          </NavLink>
        </nav>
      )}
    </div>
  );
}

export default MainLayout;
