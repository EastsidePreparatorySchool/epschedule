import React, { createContext, useContext, useState } from 'react';

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [toast, setToast] = useState(null);
  const [popup, setPopup] = useState(null);

  function showToast(message) {
    setToast(message);
    setTimeout(() => setToast(null), 10000);
  }

  function openPopup(title, contentType, data) {
    setPopup({ title, contentType, data });
  }

  function closePopup() {
    setPopup(null);
  }

  return (
    <AppContext.Provider value={{ toast, showToast, popup, openPopup, closePopup }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useAppContext must be used within AppProvider');
  return ctx;
}
