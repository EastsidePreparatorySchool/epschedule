import React, { useState, useEffect } from "react";
import { AppProvider, useAppContext } from "./context/AppContext";
import Header from "./components/Header";
import Drawer from "./components/Drawer";
import Schedule from "./components/Schedule";
import PopupPanel from "./components/PopupPanel";
import Toast from "./components/Toast";
import SettingsDialog from "./components/SettingsDialog";
import AboutDialog from "./components/AboutDialog";
import GitHubDialog from "./components/GitHubDialog";
import {
  getInitialDate,
  adjustDate,
  dateToNextTri,
  copyDate,
} from "./utils/dateUtils";
import { buildScheduleEntries } from "./utils/scheduleHelpers";

function AppInner() {
  const appData = window.APP_DATA || {};
  const {
    userSchedule,
    days,
    lunches,
    termStarts = [],
    latestCommits,
    username,
    version,
    sharePhoto,
    isAdmin,
  } = appData;

  const triStartDates = (termStarts || []).map((d) => new Date(d));

  const [currentDate, setCurrentDate] = useState(() => getInitialDate());
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [githubOpen, setGithubOpen] = useState(false);
  const { popup, closePopup, toast } = useAppContext();

  const { entries, allDayEvent } = buildScheduleEntries(
    currentDate,
    userSchedule,
    "full",
    days,
    lunches,
    triStartDates,
    userSchedule,
  );

  useEffect(() => {
    function handleKey(e) {
      if (drawerOpen) return;
      if (!popup && !searchOpen) {
        if (e.keyCode === 37) {
          const d = copyDate(currentDate);
          adjustDate(d, -1);
          setCurrentDate(d);
        } else if (e.keyCode === 39) {
          const d = copyDate(currentDate);
          adjustDate(d, 1);
          setCurrentDate(d);
        } else if (e.keyCode === 191) {
          setSearchOpen(true);
        }
      } else if (searchOpen && e.keyCode === 27) {
        setSearchOpen(false);
      } else if (popup && e.keyCode === 27) {
        closePopup();
      }
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [drawerOpen, popup, searchOpen, currentDate, closePopup]);

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
  function handleDateSelect(dateStr) {
    const parts = dateStr.split("-");
    setCurrentDate(new Date(parts[0], parts[1] - 1, parts[2]));
  }
  function handleNextTri() {
    setCurrentDate(dateToNextTri(currentDate, triStartDates));
  }

  return (
    <div className="app-root">
      <Header
        currentDate={currentDate}
        isAdmin={isAdmin}
        drawerOpen={drawerOpen}
        searchOpen={searchOpen}
        onMenuClick={() => setDrawerOpen((o) => !o)}
        onDateBack={handleDateBack}
        onDateForward={handleDateForward}
        onDateSelect={handleDateSelect}
        onNextTri={handleNextTri}
        onSearchOpen={() => setSearchOpen(true)}
        onSearchClose={() => setSearchOpen(false)}
      />
      <Drawer
        open={drawerOpen}
        version={version}
        onClose={() => setDrawerOpen(false)}
        onSignOut={() =>
          import("./utils/api").then((m) =>
            m.logout().then(() => location.reload()),
          )
        }
        onSettings={() => {
          setDrawerOpen(false);
          setSettingsOpen(true);
        }}
        onBug={() => {
          setDrawerOpen(false);
          window.open("https://forms.office.com/r/rwmhK8xw44");
        }}
        onGitHub={() => {
          setDrawerOpen(false);
          setGithubOpen(true);
        }}
        onAbout={() => {
          setDrawerOpen(false);
          setAboutOpen(true);
        }}
      />
      {drawerOpen && (
        <div className="drawer-overlay" onClick={() => setDrawerOpen(false)} />
      )}
      <main className="main-content">
        <Schedule
          entries={entries}
          allDayEvent={allDayEvent}
          onDateBack={handleDateBack}
          onDateForward={handleDateForward}
          currentDate={currentDate}
          days={days}
          lunches={lunches}
          triStartDates={triStartDates}
          userSchedule={userSchedule}
          username={username}
          sharePhoto={sharePhoto}
        />
      </main>
      {popup && (
        <PopupPanel
          title={popup.title}
          contentType={popup.contentType}
          data={popup.data}
          onClose={closePopup}
          currentDate={currentDate}
          days={days}
          lunches={lunches}
          triStartDates={triStartDates}
          userSchedule={userSchedule}
          username={username}
          sharePhoto={sharePhoto}
        />
      )}
      {toast && <Toast message={toast} />}
      {settingsOpen && (
        <SettingsDialog
          sharePhoto={sharePhoto}
          onClose={() => setSettingsOpen(false)}
        />
      )}
      {aboutOpen && <AboutDialog onClose={() => setAboutOpen(false)} />}
      {githubOpen && (
        <GitHubDialog
          commits={latestCommits}
          onClose={() => setGithubOpen(false)}
        />
      )}
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <AppInner />
    </AppProvider>
  );
}
