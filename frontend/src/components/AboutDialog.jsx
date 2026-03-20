import React from "react";

export default function AboutDialog({ onClose }) {
  return (
    <div
      className="dialog-overlay"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="dialog about-dialog">
        <h2>About</h2>
        <div>
          <p>
            <strong>EPSchedule Club:</strong>
          </p>
          <p>---A club designated to maintain this website and add changes</p>
          <p>---We meet in TMAC-007, every Thursday during Middle Band</p>
        </div>
        <div>
          <p>
            <strong>Club Leaders: Anmol Josan and Rishi Pudipeddi</strong>
          </p>
          <p>
            <a href="mailto:ajosan@eastsideprep.org">ajosan@eastsideprep.org</a>
          </p>
          <p>
            <a href="mailto:rpudipeddi@eastsideprep.org">
              rpudipeddi@eastsideprep.org
            </a>
          </p>
          <p>---Club leaders and managers of this project</p>
        </div>
        <div>
          <p>
            <strong>Connor West</strong>
          </p>
          <p>
            <a href="mailto:cwest@eastsideprep.org">cwest@eastsideprep.org</a>
          </p>
          <p>---fixed the website</p>
        </div>
        <button className="dialog-close-btn" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
}
