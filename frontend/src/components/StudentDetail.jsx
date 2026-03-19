import React from 'react';
import ScheduleLite from './ScheduleLite';

export default function StudentDetail({
  personData,
  currentDate,
  days,
  lunches,
  triStartDates,
  userSchedule,
  username,
  sharePhoto,
}) {
  if (!personData) return <div className="loading">Loading...</div>;

  const displayName = personData.preferred_name || personData.firstname;
  const isTeacher = !personData.grade;
  const isCurrentUser = personData.username === username;

  return (
    <div className="student-detail">
      <div className="student-detail-header">
        {isCurrentUser && !sharePhoto && (
          <div className="photo-sharing-notice">
            You have photo sharing turned off, so others cannot see your photo
          </div>
        )}
        {personData.username === 'cwest' ? (
          <a href="https://connorwe.st">
            <img
              src={`${personData.photo_url}?t=${Date.now()}`}
              className="student-large-photo"
              alt={displayName}
              onError={(e) => {
                if (e.target.src !== window.location.origin + '/static/images/placeholder.png') {
                  e.target.src = '/static/images/placeholder.png';
                }
              }}
            />
          </a>
        ) : (
          <img
            src={`${personData.photo_url}?t=${Date.now()}`}
            className="student-large-photo"
            alt={displayName}
            onError={(e) => {
              if (e.target.src !== window.location.origin + '/static/images/placeholder.png') {
                e.target.src = '/static/images/placeholder.png';
              }
            }}
          />
        )}
        <div className="student-detail-info">
          {personData.grade && <h3 className="student-grade">{personData.grade}th Grade</h3>}
          <p>
            <a href={`mailto:${personData.email.toLowerCase()}`}>Email {displayName}</a>
          </p>
          {!isTeacher && personData.advisor && (
            <p>
              Advisor:{' '}
              {personData.advisor.charAt(1).toUpperCase() + personData.advisor.slice(2)}
            </p>
          )}
          {isTeacher && personData.office && <p>Office: {personData.office}</p>}
          {isTeacher &&
            personData.bio &&
            personData.bio.map((para, i) => <p key={i}>{para}</p>)}
        </div>
      </div>
      <ScheduleLite
        personData={personData}
        initialDate={currentDate}
        days={days}
        lunches={lunches}
        triStartDates={triStartDates}
        userSchedule={userSchedule}
      />
    </div>
  );
}
