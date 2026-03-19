import React, { useRef } from 'react';
import ScheduleCard from './ScheduleCard';

export default function Schedule({
  entries,
  allDayEvent,
  onDateBack,
  onDateForward,
  currentDate,
  days,
  lunches,
  triStartDates,
  userSchedule,
  username,
  sharePhoto,
}) {
  const touchStartX = useRef(null);

  function handleTouchStart(e) {
    touchStartX.current = e.touches[0].clientX;
  }
  function handleTouchEnd(e) {
    if (touchStartX.current === null) return;
    const dx = e.changedTouches[0].clientX - touchStartX.current;
    if (Math.abs(dx) > 50) {
      if (dx < 0) onDateForward();
      else onDateBack();
    }
    touchStartX.current = null;
  }

  return (
    <div
      className="schedule-container"
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      {allDayEvent ? (
        <div className="all-day-event">
          <img
            src={allDayEvent.url}
            alt={allDayEvent.text}
            className="all-day-image"
          />
          <p className="all-day-text">{allDayEvent.text}</p>
        </div>
      ) : entries && entries.length > 0 ? (
        <div className="schedule-list">
          {entries.map((entry, i) => (
            <ScheduleCard
              key={`${entry.period}-${entry.name}-${i}`}
              entry={entry}
              currentDate={currentDate}
              userSchedule={userSchedule}
            />
          ))}
        </div>
      ) : (
        <div className="schedule-empty">No schedule available</div>
      )}
    </div>
  );
}
