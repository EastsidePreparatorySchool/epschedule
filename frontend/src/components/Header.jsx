import React, { useState, useRef, useEffect } from "react";
import { dateToString } from "../utils/dateUtils";
import { useAppContext } from "../context/AppContext";
import { fetchJSON } from "../utils/api";

export default function Header({
  currentDate,
  isAdmin,
  drawerOpen,
  searchOpen,
  onMenuClick,
  onDateBack,
  onDateForward,
  onDateSelect,
  onNextTri,
  onSearchOpen,
  onSearchClose,
}) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const searchInputRef = useRef(null);
  const { openPopup, showToast } = useAppContext();

  const dateStr = dateToString(currentDate);

  useEffect(() => {
    if (searchOpen && searchInputRef.current) {
      setTimeout(() => searchInputRef.current?.focus(), 50);
    } else {
      setQuery("");
      setSuggestions([]);
    }
  }, [searchOpen]);

  async function handleSearchChange(e) {
    const val = e.target.value;
    setQuery(val);
    if (val.length < 1) {
      setSuggestions([]);
      return;
    }
    try {
      const results = await fetchJSON(`/search/${encodeURIComponent(val)}`);
      setSuggestions(Array.isArray(results) ? results : []);
    } catch {
      setSuggestions([]);
    }
  }

  async function handleSelectSuggestion(person) {
    onSearchClose();
    setQuery("");
    setSuggestions([]);
    try {
      const data = await fetchJSON(`/student/${person.username}`);
      openPopup(person.name, "student", data);
    } catch {
      showToast("Error loading student data");
    }
  }

  const dateInputValue = `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, "0")}-${String(currentDate.getDate()).padStart(2, "0")}`;

  return (
    <header className="app-header">
      {!searchOpen ? (
        <div className="header-main">
          <button className="icon-btn" onClick={onMenuClick} aria-label="Menu">
            ☰
          </button>
          <span className="header-title">
            {dateStr}
            {isAdmin && <span className="admin-label"> Admin</span>}
          </span>
          <a
            href="https://forms.office.com/Pages/ResponsePage.aspx?id=ix5osiDdz0axYzcaLXxgFJEzcgSzDSBAmZEyMRzHSWZURUxIVzNBWjlRNzIwSTNMQTRSWkJWQzdEWi4u"
            target="_blank"
            rel="noopener noreferrer"
            className="join-button"
          >
            Join Hack Club
          </a>
          <div className="header-actions">
            <span className="datepicker-toggle">
              <span className="datepicker-toggle-button">📅</span>
              <input
                className="datepicker-input"
                type="date"
                value={dateInputValue}
                onChange={(e) => onDateSelect(e.target.value)}
              />
            </span>
            <button
              className="icon-btn"
              onClick={onDateBack}
              aria-label="Previous day"
            >
              ←
            </button>
            <button
              className="icon-btn"
              onClick={onDateForward}
              aria-label="Next day"
            >
              →
            </button>
            <span className="tooltip">
              <button
                className="icon-btn"
                onClick={onNextTri}
                aria-label="Next trimester"
              >
                »
              </button>
              <span className="tooltiptext">Skip to Next Trimester</span>
            </span>
            <button
              className="icon-btn"
              onClick={onSearchOpen}
              aria-label="Search"
            >
              🔍
            </button>
          </div>
        </div>
      ) : (
        <div className="header-search">
          <button
            className="icon-btn"
            onClick={onSearchClose}
            aria-label="Close search"
          >
            ←
          </button>
          <div className="search-container">
            <input
              ref={searchInputRef}
              className="search-input"
              type="text"
              placeholder="Search people"
              value={query}
              onChange={handleSearchChange}
              onKeyDown={(e) => {
                if (e.key === "Escape") onSearchClose();
                if (e.key === "Enter" && suggestions.length > 0)
                  handleSelectSuggestion(suggestions[0]);
              }}
            />
            {suggestions.length > 0 && (
              <ul className="search-suggestions">
                {suggestions.slice(0, 5).map((s, i) => (
                  <li
                    key={i}
                    className="search-suggestion-item"
                    onClick={() => handleSelectSuggestion(s)}
                  >
                    {s.name}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
