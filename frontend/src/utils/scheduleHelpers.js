/**
 * Schedule helper functions ported from the original Polymer frontend.
 */

import { makeDateKey } from "./dateUtils";

export const IMAGE_CDN = "https://epschedule-avatars.storage.googleapis.com/";

/** Returns 0, 1, or 2 for the current trimester index. */
export function getTermId(dateObj, triStartDates) {
  let termId = 0;
  for (let i = 0; i < 2; i++) {
    if (dateObj < triStartDates[i + 1]) {
      termId = i;
      break;
    } else {
      termId = i + 1;
    }
  }
  return termId;
}

/** Returns the array of {period, times} objects for the given date, or undefined for no school. */
export function getScheduleTypeForDate(dateObj, days) {
  const datekey = makeDateKey(dateObj);
  const day = days[0][datekey];
  return days[1][day];
}

/** Returns "MS" for grade ≤8, otherwise "US". */
export function getSchool(grade) {
  return grade <= 8 ? "MS" : "US";
}

/** Returns true for standard class periods (A–H plus Advisory). */
export function isStandardClass(letter) {
  return (
    ["O", "A", "B", "C", "D", "E", "F", "G", "H", "Advisory"].indexOf(letter) >=
    0
  );
}

/** Returns the lunch entry for the given date, or undefined. */
export function getLunchForDate(lunches, date) {
  for (let i = 0; i < lunches.length; i++) {
    const lunch = lunches[i];
    if (
      date.getDate() === lunch.day &&
      date.getMonth() + 1 === lunch.month &&
      date.getFullYear() === lunch.year
    ) {
      return lunch;
    }
  }
  return undefined;
}

/** Builds the EPSpaces room map URL for a given room string. */
export function linkFromRoom(room) {
  const dashIdx = room.indexOf("-");
  const building = room.substring(0, dashIdx).toUpperCase();
  const floor = room.substring(dashIdx + 1, dashIdx + 2).toUpperCase();
  const newRoom =
    building +
    "_" +
    floor +
    "_" +
    room.substring(dashIdx + 1).replace(/[^A-Za-z0-9]/g, "");
  return `http://epspaces.madeateps.org/?building=${building}&floor=${floor}&room=${newRoom}`;
}

/** Returns true if the OS/browser is in dark mode. */
export function isDarkMode() {
  return (
    window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
  );
}

/** Attaches avatar and link fields to a scheduleObj in-place. */
function addScheduleImages(scheduleObj, type) {
  if (scheduleObj.teacher !== "" || type === "core") {
    scheduleObj.avatar = IMAGE_CDN + scheduleObj.teacherUsername + ".jpg";
    scheduleObj.teacherLink =
      "/teacher/" + scheduleObj.teacher.toLowerCase().replace(/ /g, "_");
  } else if (scheduleObj.period === "X" || scheduleObj.name === "Free Period") {
    scheduleObj.teacherLink = "";
    const imageName = scheduleObj.name
      .toLowerCase()
      .replace("/", "")
      .replace(/\s/g, "")
      .replace(/(\(.*?\))/g, "");
    scheduleObj.avatar = isDarkMode()
      ? "/static/images/" + imageName + "_dark.svg"
      : "/static/images/" + imageName + ".svg";
  }
  scheduleObj.roomLink =
    "/room/" + scheduleObj.room.toLowerCase().replace(/ /g, "_");
}

/** Returns true if the given scheduleObj shares a period with the current user. */
function isSharedClass(scheduleObj, termid, userSchedule) {
  const userClasses = userSchedule.classes[termid];
  for (let i = 0; i < userClasses.length; i++) {
    const c = userClasses[i];
    if (
      c.period === scheduleObj.period &&
      c.name === scheduleObj.name &&
      (c.teacher_username != null ? c.teacher_username : "") ===
        scheduleObj.teacherUsername
    ) {
      return true;
    }
  }
  return false;
}

/** Returns true if the period label belongs to the opposite school division. */
function incorrectSchool(periodStr, school) {
  const other = school === "MS" ? "US" : "MS";
  if (periodStr.indexOf(other) !== -1) return true;
  if (school === "MS" && periodStr.indexOf("Seminars") !== -1) return true;
  return false;
}

/**
 * Creates a single schedule entry object for one time slot.
 * Returns null if the slot should be skipped.
 */
function createClassEntry(
  schedule,
  school,
  day,
  currentSlot,
  type,
  lunchInfo,
  termId,
  userSchedule,
) {
  const slotPeriod = day[currentSlot].period;

  if (school && incorrectSchool(slotPeriod, school)) return null;

  const period = slotPeriod.replace(" - " + school, "");

  let scheduleObj;
  let foundClass = false;

  if (isStandardClass(period)) {
    for (let k = 0; k < schedule.classes.length; k++) {
      const clazz = schedule.classes[k];
      if (clazz.period === period) {
        if (clazz.teacher_username) {
          const tu = clazz.teacher_username;
          const teacher = tu.charAt(1).toUpperCase() + tu.slice(2);
          scheduleObj = {
            name: clazz.name,
            teacher,
            teacherUsername: clazz.teacher_username,
            room: clazz.room,
            period,
            time: "",
          };
          if (type === "core") {
            scheduleObj.studentCount = clazz.students
              ? clazz.students.toString()
              : "0";
          }
        } else {
          scheduleObj = {
            name: clazz.name,
            teacher: "",
            teacherUsername: "",
            room: "",
            period,
            time: "",
          };
        }
        foundClass = true;
        break;
      }
    }
    if (!foundClass) return null;
  } else {
    scheduleObj = {
      name: period,
      teacher: "",
      room: "",
      period: "X",
      time: "",
    };
    const LPC_COMMONS_CLASSES = [
      "Assembly",
      "US Community",
      "Lunch (US)",
      "Lunch (MS)",
    ];
    if (LPC_COMMONS_CLASSES.includes(scheduleObj.name)) {
      scheduleObj.room = "LPC Commons";
    }
    if (
      scheduleObj.name === "Lunch (US)" ||
      scheduleObj.name === "Lunch (MS)"
    ) {
      scheduleObj.lunchInfo = lunchInfo;
    }
  }

  if (scheduleObj.teacher === "N/A") scheduleObj.teacher = "";
  if (scheduleObj.room === "N/A") scheduleObj.room = "";

  if (type === "full" || type === "core") {
    addScheduleImages(scheduleObj, type);
  } else if (type === "lite") {
    if (isStandardClass(scheduleObj.period)) {
      scheduleObj.shared = isSharedClass(
        scheduleObj,
        schedule.termid,
        userSchedule,
      );
      if (scheduleObj.teacher) {
        const parts = scheduleObj.teacher.split(" ");
        scheduleObj.teacherLastName = parts[parts.length - 1];
      }
    } else {
      return null; // skip non-class slots in lite view
    }
  }

  scheduleObj.termId = termId;

  if (type !== "core") {
    const times = day[currentSlot].times.split("-");
    scheduleObj.startTime = times[0].trim();
    scheduleObj.endTime = times[1].trim();
  }

  return scheduleObj;
}

/**
 * Main schedule-building function.
 * Returns { entries: [...] | null, allDayEvent: null | { url, text } }
 */
export function buildScheduleEntries(
  dateObj,
  schedule,
  type,
  days,
  lunches,
  triStartDates,
  userSchedule,
) {
  if (!schedule || !days) {
    return {
      entries: null,
      allDayEvent: {
        url: "/static/images/epslogolarge.png",
        text: "No School",
      },
    };
  }

  const termId = getTermId(dateObj, triStartDates);
  let school = null;
  if ((type === "full" || type === "lite") && schedule.grade != null) {
    school = getSchool(schedule.grade);
  }

  const lunchInfo =
    type === "full" ? getLunchForDate(lunches || [], dateObj) : null;

  // Core type: build from each class in the trimester, not from the day schedule
  if (type === "core") {
    const termClasses =
      schedule.classes && schedule.classes[termId]
        ? schedule.classes[termId]
        : [];
    const todaySchedule = [];
    for (let i = 0; i < termClasses.length; i++) {
      const fakeDay = [{ period: termClasses[i].period, times: "" }];
      const obj = createClassEntry(
        { classes: [termClasses[i]] },
        school,
        fakeDay,
        0,
        type,
        lunchInfo,
        termId,
        userSchedule,
      );
      if (obj) todaySchedule.push(obj);
    }
    return { entries: todaySchedule, allDayEvent: null };
  }

  const day = getScheduleTypeForDate(dateObj, days);

  if (!day) {
    return {
      entries: null,
      allDayEvent: {
        url: "/static/images/epslogolarge.png",
        text: "No School",
      },
    };
  }
  if (day.length === 1) {
    return {
      entries: null,
      allDayEvent: {
        url: "/static/images/epslogolarge.png",
        text: day[0].period,
      },
    };
  }

  const triSchedule = JSON.parse(JSON.stringify(schedule));
  triSchedule.classes = triSchedule.classes[termId];
  triSchedule.termid = termId;

  const todaySchedule = [];
  for (let slot = 0; slot < day.length; slot++) {
    const obj = createClassEntry(
      triSchedule,
      school,
      day,
      slot,
      type,
      lunchInfo,
      termId,
      userSchedule,
    );
    if (obj) todaySchedule.push(obj);
  }

  if (schedule.early_dismissal && todaySchedule.length > 0) {
    const last = todaySchedule[todaySchedule.length - 1];
    todaySchedule.push({
      name: "Early Dismissal",
      teacher: "",
      teacherUsername: "",
      room: "",
      period: "ED",
      time: "",
      startTime: last.endTime,
      endTime: last.endTime,
      avatar: isDarkMode()
        ? "/static/images/earlydismissal_dark.svg"
        : "/static/images/earlydismissal.svg",
      teacherLink: "",
      roomLink: "",
      termId,
    });
  }

  return { entries: todaySchedule, allDayEvent: null };
}
