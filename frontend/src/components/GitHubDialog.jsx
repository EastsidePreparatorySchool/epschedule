import React from "react";

export default function GitHubDialog({ commits, onClose }) {
  return (
    <div
      className="dialog-overlay"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="dialog github-dialog">
        <h1>
          <a
            href="https://github.com/EastsidePreparatorySchool/epschedule"
            className="github-title-link"
          >
            Latest Github Updates
          </a>
        </h1>
        <div className="github-commits" id="GithubUpdateBox">
          {commits &&
            commits.map((commit, i) => {
              const date = new Date(commit.date + " UTC");
              return (
                <a
                  key={i}
                  href={commit.url}
                  className="github-commit-link GithubLink"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {commit.name};<br />
                  Committed by {commit.author} at {date.toLocaleString("en-US")}
                  <br />
                  <br />
                </a>
              );
            })}
        </div>
        <button className="dialog-close-btn" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
}
