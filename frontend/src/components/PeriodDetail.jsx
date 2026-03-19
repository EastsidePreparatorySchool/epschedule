import React from 'react';
import { buildScheduleEntries } from '../utils/scheduleHelpers';
import { copyDate } from '../utils/dateUtils';

export default function PeriodDetail({
  periodData,
  currentDate,
  days,
  lunches,
  triStartDates,
  userSchedule,
}) {
  if (!periodData) return <div className="loading">Loading...</div>;

  // Build list of alternate classes for this period (core type)
  const { entries: altEntries } = buildScheduleEntries(
    copyDate(currentDate),
    periodData,
    'core',
    days,
    lunches,
    triStartDates,
    userSchedule
  );

  // Build the single current class entry
  const currentClass = periodData.currentclass;
  const currentEntries = currentClass ? [currentClass] : [];

  function stringifyRooms(arr) {
    if (!arr || arr.length === 0) return 'None';
    return arr.join(', ');
  }

  return (
    <div className="period-detail">
      <div className="period-column">
        <div className="period-subcontainer">
          <div className="period-heading">Other classes to take:</div>
          <div className="period-schedule">
            {altEntries && altEntries.length > 0 ? (
              altEntries.map((entry, i) => (
                <div key={i} className="period-alt-entry">
                  <strong>{entry.name}</strong>
                  {entry.teacher && <span> — {entry.teacher}</span>}
                </div>
              ))
            ) : (
              <div className="period-none">None</div>
            )}
          </div>
        </div>
      </div>
      <div className="period-column">
        <div className="period-subcontainer">
          <div className="period-heading">Empty rooms:</div>
          <div className="freeroomswarning">
            These are the classrooms without a class taking place this period. You may use them
            to work or study as you choose.
          </div>
          <div>{stringifyRooms(periodData.freerooms)}</div>
        </div>
        <div className="period-subcontainer">
          <div className="period-heading">Current class:</div>
          {currentEntries.map((entry, i) => (
            <div key={i} className="period-current-entry">
              <strong>{entry.name}</strong>
              {entry.teacher && <span> — {entry.teacher}</span>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
