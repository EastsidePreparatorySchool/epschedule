import React from "react";
import ReactDOM from "react-dom/client";
import LoginPage from "./LoginPage";
import "./login.css";

ReactDOM.createRoot(document.getElementById("login-app")).render(
  <React.StrictMode>
    <LoginPage />
  </React.StrictMode>,
);
