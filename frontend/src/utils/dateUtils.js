/**
 * Date utility functions ported from the original Polymer frontend.
 */

/** Returns today's date, advancing to Monday if it's Saturday or Sunday. */
export function getInitialDate() {
  const date = new Date();
  if (date.getDay() === 6) {
    date.setDate(date.getDate() + 2); // Saturday → Monday
  } else if (date.getDay() === 0) {
    date.setDate(date.getDate() + 1); // Sunday → Monday
  }
  return date;
}

/**
 * Mutates `date` by adding `delta` days, skipping weekends.
 * delta must be 1 or -1.
 */
export function adjustDate(date, delta) {
  date.setDate(date.getDate() + delta);
  if (date.getDay() === 6 && delta === 1) {
    date.setDate(date.getDate() + 2); // Friday+1 → Monday
  } else if (date.getDay() === 0 && delta === -1) {
    date.setDate(date.getDate() - 2); // Monday-1 → Friday
  }
}

/** Returns a human-readable string like "Monday, 3/17". */
export function dateToString(date) {
  const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  return DAYS[date.getDay()] + ', ' + (date.getMonth() + 1) + '/' + date.getDate();
}

/** Returns a zero-padded YYYY-MM-DD string for use as a lookup key. */
export function makeDateKey(date) {
  function toTwoDig(num) {
    return num.toString().length === 1 ? '0' + num : num.toString();
  }
  return date.getFullYear() + '-' + toTwoDig(date.getMonth() + 1) + '-' + toTwoDig(date.getDate());
}

/** Returns true if `d1` represents the same calendar day as today. */
export function dateIsCurrentDay(d1) {
  const d2 = new Date();
  return (
    d1.getDate() === d2.getDate() &&
    d1.getMonth() === d2.getMonth() &&
    d1.getYear() === d2.getYear()
  );
}

/** Returns a shallow copy of a Date object. */
export function copyDate(date) {
  return new Date(date.getTime());
}

/**
 * Returns the first school day of the next trimester.
 * If all trimester start dates are in the past, wraps to the first trimester.
 */
export function dateToNextTri(currentDate, triStartDates) {
  let goToTri = -1;
  for (let i = 0; i < 3; i++) {
    if (currentDate < triStartDates[i]) {
      goToTri = i;
      break;
    }
  }
  if (goToTri === -1) goToTri = 0;

  // Start from the trimester boundary and advance to the next weekday.
  const newDate = new Date(triStartDates[goToTri]);
  newDate.setDate(newDate.getDate() + 1);
  if (newDate.getDay() === 6) {
    newDate.setDate(newDate.getDate() + 2);
  } else if (newDate.getDay() === 0) {
    newDate.setDate(newDate.getDate() + 1);
  }
  return newDate;
}
