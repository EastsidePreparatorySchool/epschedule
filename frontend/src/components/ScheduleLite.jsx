import React, { useState, useRef } from "react";
import { dateToString, adjustDate, copyDate } from "../utils/dateUtils";
import { buildScheduleEntries, linkFromRoom } from "../utils/scheduleHelpers";
import { useAppContext } from "../context/AppContext";
import { fetchJSON } from "../utils/api";

export default function ScheduleLite({
  personData,
  initialDate,
  days,
  lunches,
  triStartDates,
  userSchedule,
}) {
  const [currentDate, setCurrentDate] = useState(() => copyDate(initialDate));
  const { openPopup, showToast } = useAppContext();
  const touchStartX = useRef(null);

  const { entries, allDayEvent } = buildScheduleEntries(
    currentDate,
    personData,
    "lite",
    days,
    lunches,
    triStartDates,
    userSchedule,
  );

  function handleDateBack() {
    const d = copyDate(currentDate);
    adjustDate(d, -1);
    setCurrentDate(d);
  }
  function handleDateForward() {
    const d = copyDate(currentDate);
    adjustDate(d, 1);
    setCurrentDate(d);
  }
  function handleTouchStart(e) {
    touchStartX.current = e.touches[0].clientX;
  }
  function handleTouchEnd(e) {
    if (!touchStartX.current) return;
    const dx = e.changedTouches[0].clientX - touchStartX.current;
    if (Math.abs(dx) > 50) {
      dx < 0 ? handleDateForward() : handleDateBack();
    }
    touchStartX.current = null;
  }

  return (
    <div
      className="schedule-lite"
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      <div className="lite-date-nav">
        <button
          className="lite-nav-btn"
          onClick={handleDateBack}
          aria-label="Previous day"
        >
          ←
        </button>
        <span className="lite-date">{dateToString(currentDate)}</span>
        <button
          className="lite-nav-btn"
          onClick={handleDateForward}
          aria-label="Next day"
        >
          →
        </button>
      </div>
      {allDayEvent ? (
        <div className="lite-no-school">{allDayEvent.text}</div>
      ) : entries && entries.length > 0 ? (
        entries.map((entry, i) => (
          <div
            key={i}
            className={`lite-card${entry.name === "Hidden" ? " lite-hidden" : ""}`}
          >
            <div
              className={`lite-shared ${entry.shared ? "shared" : "not-shared"}`}
            />
            <div className="lite-info">
              <p className="lite-time">
                {entry.startTime} – {entry.endTime}
                {entry.teacherLastName && entry.room && (
                  <>
                    {" "}
                    ({entry.teacherLastName},{" "}
                    <a
                      href={linkFromRoom(entry.room)}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {entry.room}
                    </a>
                    )
                  </>
                )}
                {entry.teacherLastName && !entry.room && (
                  <> ({entry.teacherLastName})</>
                )}
                {!entry.teacherLastName && entry.room && (
                  <>
                    {" "}
                    (
                    <a
                      href={linkFromRoom(entry.room)}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {entry.room}
                    </a>
                    )
                  </>
                )}
              </p>
              <p className="lite-name">{entry.name}</p>
            </div>
          </div>
        ))
      ) : (
        <div className="lite-no-school">No classes</div>
      )}
    </div>
  );
}
