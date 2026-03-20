import React, { useEffect } from "react";
import StudentDetail from "./StudentDetail";
import PeriodDetail from "./PeriodDetail";

export default function PopupPanel({
  title,
  contentType,
  data,
  onClose,
  currentDate,
  days,
  lunches,
  triStartDates,
  userSchedule,
  username,
  sharePhoto,
}) {
  useEffect(() => {
    function handleKey(e) {
      if (e.keyCode === 27) onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  return (
    <div className="popup-overlay">
      <div className="popup-panel">
        <div className="popup-header">
          <button
            className="icon-btn popup-back"
            onClick={onClose}
            aria-label="Back"
          >
            ←
          </button>
          <span className="popup-title">{title}</span>
        </div>
        <div className="popup-content">
          {contentType === "student" && (
            <StudentDetail
              personData={data}
              currentDate={currentDate}
              days={days}
              lunches={lunches}
              triStartDates={triStartDates}
              userSchedule={userSchedule}
              username={username}
              sharePhoto={sharePhoto}
            />
          )}
          {contentType === "period" && (
            <PeriodDetail
              periodData={data}
              currentDate={currentDate}
              days={days}
              lunches={lunches}
              triStartDates={triStartDates}
              userSchedule={userSchedule}
            />
          )}
        </div>
      </div>
    </div>
  );
}
