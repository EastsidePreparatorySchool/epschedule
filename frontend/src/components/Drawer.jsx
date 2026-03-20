import React from "react";

export default function Drawer({
  open,
  version,
  onClose,
  onSignOut,
  onSettings,
  onBug,
  onGitHub,
  onAbout,
}) {
  return (
    <nav className={`drawer ${open ? "drawer-open" : ""}`}>
      <div className="drawer-content">
        <div className="image-container">
          <img src="/static/images/epslogo.jpg" alt="EPS Logo" />
        </div>
        <button className="drawer-item" onClick={onSignOut}>
          <span className="drawer-icon">👤</span>
          <span>Sign out</span>
        </button>
        <button className="drawer-item" onClick={onSettings}>
          <span className="drawer-icon">⚙️</span>
          <span>Settings</span>
        </button>
        <button className="drawer-item" onClick={onBug}>
          <span className="drawer-icon">🐛</span>
          <span>Report a bug</span>
        </button>
        <button className="drawer-item" onClick={onGitHub}>
          <span className="drawer-icon">📋</span>
          <span>See Latest Changes</span>
        </button>
        <button className="drawer-item" onClick={onAbout}>
          <span className="drawer-icon">ℹ️</span>
          <span>About</span>
        </button>
        <div className="drawer-version">v{version}</div>
      </div>
    </nav>
  );
}
