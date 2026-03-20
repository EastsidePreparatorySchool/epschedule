import React, { useState } from "react";
import { useAppContext } from "../context/AppContext";
import { getClassData, fetchJSON } from "../utils/api";
import { linkFromRoom } from "../utils/scheduleHelpers";

const EXPANDABLE_PERIODS = ["A", "B", "C", "D", "E", "F", "G", "H", "Advisory"];

export default function ScheduleCard({ entry, currentDate, userSchedule }) {
  const [expanded, setExpanded] = useState(false);
  const [students, setStudents] = useState(null);
  const [loading, setLoading] = useState(false);
  const { openPopup, showToast } = useAppContext();

  const isLunch = Boolean(entry.lunchInfo);
  const isExpandable = EXPANDABLE_PERIODS.includes(entry.period) || isLunch;

  async function handleCardClick() {
    if (!isExpandable) return;

    if (expanded) {
      setExpanded(false);
      return;
    }

    if (isLunch) {
      setExpanded(true);
      return;
    }

    if (!students) {
      setLoading(true);
      try {
        const data = await getClassData(entry.period, entry.termId);
        setStudents(data.students || []);
      } catch {
        showToast("Error loading class data");
        setLoading(false);
        return;
      }
      setLoading(false);
    }
    setExpanded(true);
  }

  async function handleTeacherClick(e) {
    e.stopPropagation();
    if (!entry.teacherUsername) return;
    try {
      const data = await fetchJSON(`/student/${entry.teacherUsername}`);
      openPopup(entry.teacher, "student", data);
    } catch {
      showToast("Error loading teacher data");
    }
  }

  async function handleStudentClick(e, student) {
    e.stopPropagation();
    const studentUsername = student.email.slice(0, -17); // strip @eastsideprep.org
    const name = student.firstname + " " + student.lastname;
    try {
      const data = await fetchJSON(`/student/${studentUsername}`);
      openPopup(name, "student", data);
    } catch {
      showToast("Error loading student data");
    }
  }

  async function handlePeriodClick(e) {
    e.stopPropagation();
    try {
      const data = await fetchJSON(`/period/${entry.period}`);
      openPopup(`${entry.period} Period`, "period", {
        ...data,
        currentclass: entry,
      });
    } catch {
      showToast("Error loading period data");
    }
  }

  function buildEmailURL() {
    if (!students) return "#";
    return "mailto:" + students.map((s) => s.email).join(";");
  }

  const teacherLastName = entry.teacher
    ? entry.teacher.split(" ").slice(-1)[0]
    : "";

  return (
    <div
      className={`schedule-card${expanded ? " expanded" : ""}`}
      onClick={handleCardClick}
      style={{ cursor: isExpandable ? "pointer" : "default" }}
    >
      <div className="card-header">
        {entry.avatar && (
          <img
            src={entry.avatar}
            className="card-avatar"
            alt={entry.teacher || entry.name}
            onError={(e) => {
              if (
                e.target.src !==
                window.location.origin + "/static/images/placeholder_small.png"
              ) {
                e.target.src = "/static/images/placeholder_small.png";
              }
            }}
          />
        )}
        <div className="card-info">
          <p className="card-time">
            {entry.startTime &&
              entry.endTime &&
              `${entry.startTime} – ${entry.endTime} `}
            {entry.teacher && entry.room && (
              <>
                (
                <span className="teacher-link" onClick={handleTeacherClick}>
                  {teacherLastName}
                </span>
                ,{" "}
                <a
                  href={linkFromRoom(entry.room)}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                >
                  {entry.room}
                </a>
                , {entry.period} Period)
              </>
            )}
            {entry.teacher && !entry.room && (
              <>
                (
                <span className="teacher-link" onClick={handleTeacherClick}>
                  {teacherLastName}
                </span>
                )
              </>
            )}
            {!entry.teacher && entry.room && (
              <>
                (
                <a
                  href={linkFromRoom(entry.room)}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                >
                  {entry.room}
                </a>
                )
              </>
            )}
          </p>
          <h2 className="card-name">{entry.name.replace(/&/g, "and")}</h2>
          {entry.lunchInfo && (
            <p className="card-lunch-summary">{entry.lunchInfo.summary}</p>
          )}
        </div>
        {isExpandable && (
          <div className="card-chevron">{expanded ? "▲" : "▼"}</div>
        )}
      </div>
      {expanded && (
        <div className="card-expanded">
          {isLunch ? (
            <ul className="lunch-details">
              {entry.lunchInfo.description &&
                entry.lunchInfo.description.map((line, i) => (
                  <li key={i}>{line}</li>
                ))}
            </ul>
          ) : (
            <>
              <div className="class-actions">
                <a
                  className="class-email-link"
                  href={buildEmailURL()}
                  onClick={(e) => e.stopPropagation()}
                >
                  EMAIL CLASS
                </a>
                {" | "}
                <span className="period-info-link" onClick={handlePeriodClick}>
                  PERIOD INFO
                </span>
              </div>
              {loading ? (
                <div className="loading">Loading...</div>
              ) : (
                students && (
                  <div className="student-grid">
                    {students.map((student, i) => (
                      <div
                        key={i}
                        className="student-cell"
                        onClick={(e) => handleStudentClick(e, student)}
                      >
                        <img
                          src={student.photo_url}
                          className="student-photo"
                          alt={`${student.firstname} ${student.lastname}`}
                          onError={(e) => {
                            if (
                              e.target.src !==
                              window.location.origin +
                                "/static/images/placeholder_small.png"
                            ) {
                              e.target.src =
                                "/static/images/placeholder_small.png";
                            }
                          }}
                        />
                        <div className="student-name">
                          {student.firstname} {student.lastname}
                        </div>
                      </div>
                    ))}
                  </div>
                )
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
