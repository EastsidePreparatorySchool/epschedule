/* 
  index.js
  main js file holding ui for epschedule when logged in

  last edited: October 2022
  by: Jack Goetzmann
*/

// signs out user
function signOut() {
  sendPostMessage("logout", reload);
}

// reloads something (website or ui idk)
function reload(result) {
  location.reload();
}

// idk what this does
// data argument is optional
function sendPostMessage(location, successFunction, data) {
  // location is the suburl to send data to, e.g. /logout
  // successfunction is the function to call if 200 is returned
  xhr = new XMLHttpRequest();
  xhr.onreadystatechange = function() {
    if (xhr.readyState == 4) {
      result = JSON.parse(xhr.responseText);
      if (xhr.status==200) {
        successFunction(result);
      } else {
        console.log(result.error);
        renderToast(result.error);
      }
    }
  }
  xhr.open("POST", location, true);

  // if there is no data to send
  if (typeof data === "undefined") {
    xhr.send(new FormData());
  } else {
    xhr.send(data);
  }
}

// code that makes "report bug" button link to office form
function reportBug() {
  window.open("https://forms.office.com/r/rwmhK8xw44");
  // old URL =  window.open("https://github.com/EastsidePreparatorySchool/epschedule/issues");
}

// old URL for bug report button
function reportBugOld() {
  window.open("https://github.com/EastsidePreparatorySchool/epschedule/issues");
}

// code that makes "about" button open pannel
function about() {
  var about = document.getElementById("about");
  about.open();
}

// code that makes "settings" button open pannel
function openSettings() {
  var dialog = document.getElementById("dialog");
  dialog.open();
}

// changes some password (idk what)
function submitChangePassword() {
  var data = new FormData();
  var oldPassword = document.getElementById("oldpassword")
  var newPassword = document.getElementById("newpassword")
  data.append('oldpassword', oldPassword.value)
  data.append('newpassword', newPassword.value)
  xhr = new XMLHttpRequest();
  xhr.onreadystatechange = function() {
    if (xhr.readyState == 4 && xhr.status==200) {
      result = JSON.parse(xhr.responseText);
      if (!result.error) {
        renderToast("Password changed successfully.");
        oldPassword.value = "";
        newPassword.value = "";
      } else {
        console.log(result.error); // logs error if password isnt changed
        renderToast(result.error);
      }
    }
  }
  xhr.open("POST", "changepassword", true);
  xhr.send(data);
}

// code that makes the "hide/show photo or schedule" work (sliders on privacy pannel)
function submitUpdatePrivacy() {
  var share_photo = document.getElementById("sharephototoggle");
  var share_schedule = document.getElementById("sharescheduletoggle");
  sendUpdatePrivacyRequest(share_photo.checked, share_schedule.checked);
  document.getElementById("dialog").close()
}

// "ok" button on privacy pannel that submits privace preferences to cloud
function sendUpdatePrivacyRequest(share_photo, share_schedule) {
  var data = new FormData();
  data.append('share_photo', share_photo);
  data.append('share_schedule', share_schedule);

  xhr = new XMLHttpRequest();
  xhr.onreadystatechange = function() {
    if (xhr.readyState == 4 && xhr.status==200) {
      result = JSON.parse(xhr.responseText);
      if (!result.error) {
        renderToast("Settings updated!");
      } else {
        console.log(result.error); // logs error if update privace fails
        renderToast(result.error);
      }
    }
  }
  xhr.open("POST", "privacy", true);
  xhr.send(data);
}

// idk what this code does -- Probably related the 20-21 school year senior prank (depreciated code point towards this)
document.onkeydown = function(event) {
  if (pages.selected == 0) {  // no popup
    if (event.keyCode == 37) {  // left
      dateBack();
    } else if (event.keyCode == 39) {  // right
      dateForward();
    }
  } else if (pages.selected == 1) {  // no popup
    if (event.keyCode == 27) {  // escape
      closePopup();
    }
  }
}

// controls date switch on swipe left or right
function scheduleSwiped(evt) {
  if (evt.detail.direction == "left") { // if left move date forward
    dateForward();
  } else { // if not left move date back
    dateBack();
  }
}

// grabs data for schedule I think
var globalDate = getInitialDate();

// finds date and grabs data and modifies it to Monday (if on weekend) 
function getInitialDate() {
  date = new Date(); // Grabs date using api?
  switch(date.getDay()) { // Falling through is intentional here (no default so its fine) -> (0 sunday, 1 monday, ... 5 friday, 6 saturday)
    case 6: // If Saturday, move the date forward twice -- To always show Monday - Friday
      date.setDate(date.getDate() + 2);
      break;
    case 0: // If Sunday, move the date forward once -- To always show Monday - Friday
      date.setDate(date.getDate() + 1);
  }

  FIRST_DAY = new Date(2019, 8, 4); // hard coded "first day" of epschedule -- probably exists to avoid an error

  if (date < FIRST_DAY) { // if before hard coded "first day"
    date = FIRST_DAY; // sets to "first day"
  }

  return date; // returns modified date
}

// moves date back 1 day
function dateBack() {
  adjustDate(globalDate, -1); // removes 1 day to date
  updateMainSchedule(); // refreshes schedule ui
}

// move date forward 1 day
function dateForward() {
  adjustDate(globalDate, 1); // adds 1 day to date
  updateMainSchedule(); // refreshes schedule ui
}

// gets data in xx-xx-xxxx form and splits in into useable code I think
function selectDate() {
  let dateElement = document.getElementById("date");
  splitDate = dateElement.value.split("-");
  globalDate = new Date(splitDate[0], splitDate[1] - 1, splitDate[2]);
  console.log(globalDate);
  updateMainSchedule();
}

// sets date to end of fall tri
function skipToWinter() {
  globalDate.setDate(fallTriEndDate.getDate());
  dateForward();
}

// sets date to end of winter tri
function skipToSpring() {
  globalDate.setDate(wintTriEndDate.getDate());
  dateForward();
}

// takes a date and sets the date to that new date?
function copyDate(date) {
  return new Date(date.getTime());
}

// takes a date and a change value and moves the date forward or back by that amount
function adjustDate(date, delta) {
  date.setDate(date.getDate() + delta); // takes date and adds or subtracts time
  if (date.getDay() == 6 && delta == 1) { // if Saturday and would change to Sunday changes to Monday
    // jump from Saturday to Monday
    date.setDate(date.getDate() + 2);
  } else if (date.getDay() == 0 && delta == -1) { // if Sunday and would change to Saturday changes to Friday
    // jump from Sunday back to Friday
    date.setDate(date.getDate() - 2);
  }
}

// takes a day and returns the day of the week (0 sunday, 1 monday -> 5 friday, 6 saturday)
function dayOfWeekToString(day) {
  var DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  return DAYS[day];
}

// takes a date and returns a string with that date in (, month/day)
function dateToString(date) {
  return dayOfWeekToString(date.getDay()) + ', ' +
      (date.getMonth() + 1) + "/" + date.getDate();
}

// main refresh UI function
function updateMainSchedule() {
  var scheduleElement = document.getElementById('mainschedule'); // finds the html div 'mainschedule'
  renderDate(globalDate); // renders the date and initializes the UI (nonschool days will get a blank image) and (schools days will get the dropdowns)
  renderSchedule(globalDate, userSchedule, "full", scheduleElement, lunches); // adds the information to initialized UI
}

// either gavin was on crack or this a senior prank (probably both)
function renderToast(text) {
  toast = document.getElementById("toast");
  console.log("Displaying toast");
  console.log(toast);
  toast.setAttribute("text", text);
  toast.show();
}

// wait why are we doing this (J: why ARE you doing this?)
function getGpsSuccess(position, roomObj) {
  var radius = 6371000; // radius of the earth (WHY IS THIS HARDCODED/EXISTS?)
  var phi1 = position.coords.latitude * (Math.PI / 180);
  var phi2 = roomObj.latitude * (Math.PI / 180);
  var deltaPhi = (roomObj.latitude-position.coords.latitude) * (Math.PI / 180);
  var deltaLambda = (roomObj.longitude-position.coords.longitude) * (Math.PI / 180);
  var a = Math.sin(deltaPhi/2) * Math.sin(deltaPhi/2) + Math.cos(phi1) *
  Math.cos(phi2) *Math.sin(deltaLambda/2) * Math.sin(deltaLambda/2);
  var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  var d = radius * c;
  if (d > 200) {
    console.log("Too far away from EPS")
    return;
  }
  map = document.getElementById("map");
  marker = document.createElement("google-map-marker");
  marker.latitude = position.coords.latitude;
  marker.longitude = position.coords.longitude;
  marker.draggable = false;
  marker.title = "Your face";
  map.appendChild(marker);
}

// takes a number for and uses an array 
function isStandardClass(letter) {
  var standardPeriods = ["O", "A", "B", "C", "D", "E", "F", "G", "H"];
  return standardPeriods.indexOf(letter) >= 0; // returns index of number
}

// switch logic to log errors for gps
function getGpsFail(error) {
  switch(error.code) {
      case error.PERMISSION_DENIED: // if user does not allow location
          console.log("User did not allow access to GPS");
          break;
      case error.POSITION_UNAVAILABLE: // if user consented to allow location but it wasnt sent
          console.log("EPSchedule was not able to get location information");
          break;
      case error.TIMEOUT: // if user request to enable gps times out
          console.log("Request to enable GPS timed out");
          break;
      case error.UNKNOWN_ERROR: // if not any of these errors
          console.log("Geolocation failed, error unknown");
          break;
  }
}

// requests more data to be displayed (if something fails???)
function requestAdditionalData(name, type, funct) {
  // type is the type of data being requested - [class, teacher, student, room, period]
  // name is the name of the class, teacher, student, etc.
  name = cleanString(name);
  var url = type + "/" + name;
  console.log("Requesting " + url);
  xhr = new XMLHttpRequest();
  xhr.onreadystatechange = function() {
    if (xhr.readyState == 4 && xhr.status==200) {
      result = JSON.parse(xhr.responseText);
      funct(result);
    }
  }
  xhr.open("GET", url, true);
  xhr.send();
}

// more geolocating google maps stuff WHY DID GAVIN DO THIS?
function renderRoom(roomObj) {
  // renderToast("Please allow EPSchedule to use your current location"); // TODO check to see if browser allows geolocation by default*/
  // bug here that causes latitude and longitude of google map tag to not exist
  var popup = document.getElementById("popup");
  var container = document.getElementById("popupContainer");
  console.log("Latitude = " + roomObj.latitude);
  console.log("Longitude = " + roomObj.longitude);
  container.innerHTML = '<google-map latitude="47.643455" longitude="-122.198935" id="map" zoom="18" disable-default-ui fit-to-markers>' +
    // '<google-map-marker latitude="' + roomObj.latitude + '" longitude="' + roomObj.longitude + '"' +
    // 'draggable="false" title="' + roomObj.room + '"></google-map-marker>
    '</google-map>';
  /*if (navigator.geolocation) {
      var success = function(gpsObj) {
        getGpsSuccess(gpsObj, roomObj);
      }
      var fail = function() {
        getGpsFail();
      }
      navigator.geolocation.getCurrentPosition(success, fail);
  } else {
      renderToast("Your browser does not support Geolocation");
  }*/
}

// unused code for the feature to add teacher bios and display them
function renderBio(teacherBio) {
  var html = ""; // creates string
  for (var i = 0; i < teacherBio.length; ++i) { // loops through length of teacherBio
    html += '<p>' + teacherBio[i] + '</p>'; // adds it to the html with html print syntax
  }
  return html; // returns a string that can be inserted into html to print bio
}

// renders popup for teacher when searched up
function renderTeacher(teacherObj) {
  var popupContainer = document.getElementById("popupContainer"); // gets popup code
  var imgSrc = "teacher_photos_fullsize/" + teacherObj.firstname + "_"; // generates a string that correlates to a photo
  imgSrc = imgSrc + teacherObj.lastname + ".jpg"; // sets the picture to a jpg
  imgSrc = imgSrc.toLowerCase(); // removes capitals of string
  var email = teacherObj.email; // finds email and sets it to email
  popupContainer.innerHTML = '<div class="teacher" layout vertical>' + // creates a string with html code
      '<paper-material class="header" elevation="2">' +
      '<div layout horizontal center>' +
      '<img src="' + imgSrc + '" width="128px" height="128px">' +
      '<div layout vertical>' +
      '<p><a href="mailto:' + email + '""><iron-icon icon="communication:email"></iron-icon>' +
      '<span class="email">Email teacher</span></a></p>' +
      renderBio(teacherObj.bio) + '</div></div></paper-material>' +
      '<schedule-lite id="teacherschedule"></schedule-lite>' +
      '</div>';
  // wait for HTML to be parsed/applied before trying to show the schedule.
  // without this, Firefox/Safari don't display the schedule.
  setTimeout(function() {
    finishLiteSchedule(document.getElementById('teacherschedule'), teacherObj);
  }, 0);
}

// makes the room a string (or "stringifys" it)
function stringifyRooms(arr) {
  s = ""; // sets return variable to clean slate
  for (var i = 0; i < arr.length; i++) { // loops through array
    s += arr[i]; // adds the value of each item in the array to s

    // don't put a comma after the last item
    if (i != arr.length - 1) {
      s += ", ";
    }
  }
  return s; // returns stringified vairable
}

// takes period info and renders UI
function renderPeriod(periodObj) {
  var popupContainer = document.getElementById("popupContainer");

  popupContainer.innerHTML =
  '<div class="period" layout vertical>' +
    '<div class="halfwidth periodbottomspace"><paper-material class="periodsubcontainer" elevation="2">' +
      '<div class="periodheading">Other classes to take:</div>' +
      '<x-schedule id="altclassesschedule" show="all" swipe-disabled></x-schedule>' +
    '</paper-material></div>' +

    '<div class="halfwidth"><div class="periodbottomspace"><paper-material class="periodsubcontainer periodmediumpadding" elevation="2">' +
      '<div class="periodheading">Empty rooms:</div>' +
      '<div class="freeroomswarning">These are the classrooms without a class taking place this period.' +
      'You may use them to work or study as you choose. Note that there may be other students or teachers already in these rooms.</div>' +
      '<div>' + stringifyRooms(periodObj['freerooms']) + '</div>' +
    '</paper-material></div>' +
    '<div class="periodbottomspace"><paper-material class="periodsubcontainer" elevation="2">' +
      '<div class="periodheading">Current class:</div>' +
      '<x-schedule id="currentperiodclassschedule" show="all" swipe-disabled></x-schedule>' +
    '</paper-material></div></div>' +
  '</div>';

  // wait for HTML to be parsed/applied before trying to show the schedule.
  // without this, Firefox/Safari don't display the schedule.
  setTimeout(function() {
    var e = document.getElementById('altclassesschedule');
    var f = document.getElementById('currentperiodclassschedule');

    renderSchedule(copyDate(globalDate), periodObj, "core", e, {}, false);
    console.log( {'classes': [[periodObj['currentclass']]*3]});

    // we have the same item three times to simulate three trimesters
    // that way, no matter what trimester we're in, we'll always pick "currentclass"
    renderSchedule(copyDate(globalDate), {'classes': [[periodObj['currentclass']],
      [periodObj['currentclass']],[periodObj['currentclass']]]}, "core", f, {}, false);


    e.behaviors = [];
    f.behaviors = [];
  }, 20);
}

// renders popup for student when searched up
function renderStudent(studentObj) {
  var popupContainer = document.getElementById("popupContainer"); // gets popup code 
  var email = studentObj.email; // finds email and sets it to email
  email = email.toLowerCase(); // makes email all lowercase
  if (studentObj.grade) { // if student has a grade
    var grade = studentObj.grade + "th Grade"; // adds "-th" after the grade
    var name = studentObj.firstname; // adds first name after grade
  } else { // if student does not currently have a grade
    var grade = ""; // sets grade to blank
    var name = studentObj.firstname + " " + studentObj.lastname; // sets name to first and last
  }
  popupContainer.innerHTML = '<div class="teacher" layout vertical>' + // html for popup
      '<paper-material class="header" elevation="2">' +
      '<div layout horizontal center>' +
      '<img src="' + studentObj.photo_url + '" onerror="if (this.src != \'/static/images/placeholder.png\') this.src = \'/static/images/placeholder.png\';">' +
      '<div layout vertical><h3><span class="grade">' + grade + '</span></h3>' +
      '<p><a href="mailto:' + email + '""><iron-icon icon="communication:email"></iron-icon>' +
      '<span class="email">Email ' + name + '</span></a></p></div></div></paper-material>' +
      '<schedule-lite id="studentschedule"></schedule-lite>' +
      '</div>';
  // wait for HTML to be parsed/applied before trying to show the schedule.
  // without this, Firefox/Safari don't display the schedule.
  setTimeout(function() {
    finishLiteSchedule(document.getElementById('studentschedule'), studentObj);
  }, 0);
}

// generates schedule for individual
function finishLiteSchedule(scheduleElement, otherUserObj) {
  scheduleElement.date = copyDate(globalDate); // copies data from api
  scheduleElement.addEventListener("swiped", function(e) {
    adjustDate(scheduleElement.date, //adjust 
        (e.detail.direction == 'left') ? 1 : -1);
    updateLiteSchedule(scheduleElement, otherUserObj);
  });
  updateLiteSchedule(scheduleElement, otherUserObj);
}

// refreshes ui of the popschedule when you search someone up 
function updateLiteSchedule(scheduleElement, otherUserObj) {
  scheduleElement.dateString = dateToString(scheduleElement.date); // attaches date
  renderSchedule(scheduleElement.date, otherUserObj, "lite", scheduleElement); // attaches 'lite' schedule
}

// takes date stored and updates ui with that date
function renderDate(dateObj) {
  var daySpan = document.getElementById("day"); // finds date ui
  daySpan.firstChild.textContent = dateToString(dateObj); // converts date to string for ui
}

// Determine whether the user is in middle or upper school
function getSchool(grade) {
  if (grade <= 8) {
    return "MS";
  } else {
    return "US";
  }
}

// changes a one digit number to a two digit number string by adding '0' in front of the other number
function toTwoDig(num) {
  var s = num.toString();
  if (s.length == 1) {
    return "0" + s;
  } else {
    return s;
  }
}

// generates date key from date in xxxx-xx-xx (2000-01-01)
function makeDateKey(dateObj){
  var datekey = dateObj.getFullYear() + "-" + // year
      toTwoDig(dateObj.getMonth() + 1) + "-" +  // month
      toTwoDig(dateObj.getDate()); // date
  return datekey;
}

// handles exceptions, also handles special weekend schedules
function getScheduleTypeForDate(dateObj, exceptions) {
  var datekey = makeDateKey(dateObj);
  var day = exceptions[0][datekey];
  return exceptions[1][day];
}

// changes ui based on US or MS
function incorrectSchool(s, school) {
  var other = "MS";
  if (school == "MS") {
    other = "US";
  }

  if (~s.indexOf(other)) {
    return true;
  }
  if (school == "MS" && ~s.indexOf("Seminars")) {
    return true;
  }
  return false;
}

// generate basic name, teacher, room, time, and period info for a class
function createClassEntry(schedule, school, day, currentSlot, type, lunchInfo) {
  var scheduleObj;
  var foundClass = false;

  // ensure that we don't display periods for middle schoolers for upper schoolers
  if (incorrectSchool(day[currentSlot]["period"], school)) {
    return null;
  } else {
    var period = day[currentSlot]["period"].replace(" - " + school, "");
  }
  // if it is a normal period
  if (isStandardClass(period)) {
    for (var k = 0; k < schedule["classes"].length; k++) {
      var clazz = schedule["classes"][k];
      if (clazz["period"] == period) {
        if (clazz["teacher_username"]) {
          // TODO remove garbage hack
          // we cant curse smh
          var tu = clazz["teacher_username"]
          var teacher = tu.charAt(1).toUpperCase() + tu.slice(2);

          scheduleObj = { name: clazz["name"],
            teacher: teacher,
            teacherUsername: clazz["teacher_username"],
            room: clazz["room"],
            period: period,
            time: ""};

          if (type == "core") {
            scheduleObj['studentCount'] = clazz["students"].toString();
          }
        } else {
          scheduleObj = { name: schedule["classes"][k]["name"],
            teacher: "",
            teacherUsername: "",
            room: "",
            period: period,
            time: ""};
        }
        foundClass = true;
        break;
      }
    }
    if (!foundClass) { // we're looking for a period the user doesn't have, like O period
      return null;
    }
  } else { // if it is a special class, such as Lunch, Assembly, or Class Meeting

    // note that 0 Period Instrumental Music does not fall in this category
    scheduleObj = {
      name: period,
      teacher: "",
      room: "",
      period: "X",
      time: ""
    };
    LPC_COMMONS_CLASSES = ["Lunch", "Assembly", "US Community"];
    if (LPC_COMMONS_CLASSES.includes(scheduleObj.name)) {

      scheduleObj.room = "LPC Commons";
    }
    if (scheduleObj.name == "Lunch (US)" || scheduleObj.name == "Lunch (MS)") {
      scheduleObj.lunchInfo = lunchInfo;
    }
  }
  if (scheduleObj.teacher == "N/A") {
    scheduleObj.teacher = "";
  }
  if (scheduleObj.room == "N/A") {
    scheduleObj.room = "";
  }
  // add in photos if the user's schedule is being rendered
  if (type == "full" || type == "core") {
    // add the left-hand images to the schedule
    addScheduleImages(scheduleObj, schedule, type);
  } else if (type == "lite") {
    if (isStandardClass(scheduleObj.period)) { // If it's a class period
      // determine if the class is shared
      scheduleObj.shared = isSharedClass(scheduleObj, schedule.termid);
    } else {
      return null; // skip over lunch, advisory, assembly, etc.
    }
  }
  scheduleObj.termId = termId;
  // split the time into the start and end times
  if (type != "core") {
    var times = day[currentSlot]["times"].split('-');
    scheduleObj.startTime = times[0].trim();
    scheduleObj.endTime = times[1].trim();
  }
  return scheduleObj;
}

// Grades on campus or each day
SPRING_2021_SCHEDULE = { // should be deleted
  "2021-04-27": [5, 6], 
  "2021-04-28": [5, 6], 
  "2021-04-29": [7, 8],
  "2021-04-30": [7, 8],
  "2021-05-03": [9, 10],
  "2021-05-04": [9, 10],
  "2021-05-05": [11, 12],
  "2021-05-06": [11, 12],
  "2021-05-07": [5, 6, 7, 8], 
  "2021-05-10": [5, 6, 7, 8], 
  "2021-05-11": [5, 6, 7, 8], 
  "2021-05-12": [5, 6, 7, 8], 
  "2021-05-13": [9, 10, 11, 12], 
  "2021-05-14": [9, 10, 11, 12], 
  "2021-05-17": [9, 10, 11, 12], 
  "2021-05-18": [9, 10, 11, 12], 
  "2021-05-19": [5, 6, 7, 8], 
  "2021-05-20": [5, 6, 7, 8], 
  "2021-05-24": [5, 6, 7, 8], 
  "2021-05-25": [5, 6, 7, 8], 
  "2021-05-26": [9, 10, 11, 12], 
  "2021-05-27": [9, 10, 11, 12], 
  "2021-05-28": [9, 10, 11, 12], 
  "2021-06-01": [9, 10, 11, 12], 
}
function isOnCampus(grade, dateObj) {
  datekey = makeDateKey(dateObj);
  ourDate = SPRING_2021_SCHEDULE[datekey];
  if (ourDate) { 
    return ourDate.includes(grade);
  } else {
    return false;
  }
}

// random image
IMAGE_CDN = "https://epschedule-avatars.storage.googleapis.com/"

// add the images on the left side to full schedules
function addScheduleImages(scheduleObj, userSchedule, type) {
  if (scheduleObj.teacher != "" || type == "core" ) {
    var sanitized_teacher_name;
    sanitized_teacher_name = scheduleObj.teacher.toLowerCase();
    sanitized_teacher_name = sanitized_teacher_name.replace(/ /g,"_");
    scheduleObj.avatar = IMAGE_CDN + scheduleObj.teacherUsername + ".jpg";
    scheduleObj.teacherLink = "/teacher/" + sanitized_teacher_name;

  // if class is a special class or free period
  } else if (scheduleObj.period == "X" || scheduleObj.name == "Free Period") {
    scheduleObj.teacherLink = "";
    var image_name = scheduleObj.name.toLowerCase();
    image_name = image_name.replace("/", "");
    image_name = image_name.replace(/\s/g, '');
    image_name = image_name.replace(/(\(.*?\))/g, ""); // Remove text between parentheses
    scheduleObj.avatar = "/static/images/" + image_name + ".svg";
  }
  scheduleObj.roomLink = "/room/" + scheduleObj.room.toLowerCase().replace(/ /g,"_");
}

// if class is shared
function isSharedClass(scheduleObj, termid) {
  var userClasses = userSchedule.classes[termid];
  for (var i = 0; i < userClasses.length; i++) {
    if (userClasses[i].period == scheduleObj.period &&
        userClasses[i].name == scheduleObj.name) {
      return true;
    }
  }
  return false;
}

// finds lunch for the date
function getLunchForDate(lunch_list, date) {
  // returns the lunch for the given date
  // if there is no lunch, returns null
  for (var i = 0; i < lunch_list.length; i++) {
    var lunch = lunch_list[i];
    // note that date.getMonth is from 0-11 but
    // all lunch date months are stored 1-12
    if (
      date.getDate() == lunch["day"] &&
      date.getMonth() + 1 == lunch["month"] &&
      date.getFullYear() == lunch["year"]
      ) {
      return lunch;
    }
  }
}

// checks if the date being shown is the current day
function dateIsCurrentDay(d1) {
  var d2 = new Date();
  return (
    d1.getDate() == d2.getDate() &&
    d1.getMonth() == d2.getMonth() &&
    d1.getYear() == d2.getYear());
}

// renders schedule
function renderSchedule(dateObj, schedule, type, scheduleElement, lunch_list, expandable = true) {

  if (dateObj > wintTriEndDate) {
    termId = 2;
  } else if (globalDate > fallTriEndDate) {
    termId = 1;
  } else {
    termId = 0;
  }
  console.log("Converted " + dateObj + " to a term ID of " + termId);
  // either MS or US
  if (type == "full" || type == "lite") { // full == yours || lite == looking at someone elses
    var school = getSchool(schedule.grade);
  }

  var todaySchedule = [];

  if (type == "full") {
    var lunchInfo = getLunchForDate(lunch_list, dateObj);
  }

  // the current schedule for that day
  var day = getScheduleTypeForDate(dateObj, days);
  if (type == "core") {
    day = [{'period': schedule["classes"][termId][0]['period'], 'times': ''}];
  }
  scheduleElement.type = type;
  scheduleElement.expandable = expandable;
  // if it is a normal day (no all day event)
  if (!day) { // If there is no school
    // get the data for the imageObj
    var imageObj = {url: "/static/images/epslogolarge.png", text: "No School"};
    scheduleElement.allDayEvent = imageObj;
    scheduleElement.entries = null; // Clear the classes
  } else if (type == "core") {
    for (var currentClass = 0; currentClass < schedule["classes"][termId].length; currentClass++) {

      var scheduleObj = createClassEntry({'classes': [schedule["classes"][termId][currentClass]]}, school, day, 0, type, lunchInfo);
      todaySchedule.push(scheduleObj);
    }
    scheduleElement.entries = todaySchedule;
    scheduleElement.allDayEvent = null;
  } else if (day.length > 1) {
    // for each class
    for (var currentSlot = 0; currentSlot < day.length; currentSlot++) {

      // render the base of the class
      var triSchedule = JSON.parse(JSON.stringify(schedule));
      triSchedule['classes'] = triSchedule['classes'][termId]
      triSchedule['termid'] = termId;
      var scheduleObj = createClassEntry(triSchedule, school, day, currentSlot, type, lunchInfo);
      if (scheduleObj) { // if scheduleObj is not null
        // to see when scheduleObj might be null, look at createClassEntry()
        // push scheduleObj to a list of class objs
        todaySchedule.push(scheduleObj);
      }
    }
    // add the list of schedules to scheduleElement's entries array
    scheduleElement.entries = todaySchedule;
    // tell the element that it is not an all day event
    scheduleElement.allDayEvent = null;
    scheduleElement.isOnCampus = isOnCampus(schedule.grade, dateObj);
  } else if (day.length == 1) { // If it is an all day event
    // get the data for the imageObj
    var imageObj = {url: '/static/images/epslogolarge.png', text: day[0]['period']};
    scheduleElement.allDayEvent = imageObj;
    scheduleElement.entries = null; // Clear the classes
  }
  // add in the expansion functions to the full schedule
  if (type == "full" || type == "core") {
    scheduleElement.onTeacherTap = function(e) {
      var username = e.model.item.teacherUsername;  
      requestAdditionalData(username, "student", renderStudent);
      openPopup(e.model.item.teacher);
    }
    scheduleElement.onStudentTap = function(e) {
      var orig_name = e.model.item.firstname + " " + e.model.item.lastname;
      var username = e.model.item.email.slice(0, -17);
      requestAdditionalData(username, "student", renderStudent);
      openPopup(orig_name);
    }
    scheduleElement.onRoomTap = function(e) {
      var orig_name = e.model.item.room;
      var name = orig_name.replace("-", "_")
      requestAdditionalData(name, "room", renderRoom);
      openPopup(orig_name);
    }
    scheduleElement.onPeriodTap = function(e) {
      requestAdditionalData(e.model.item.period, "period", renderPeriod);
      openPopup(e.model.item.period + " Period");
    }
    scheduleElement.onRate = function(rating) {
      var data = new FormData();
      data.append('rating', rating);
      sendPostMessage("lunch", ratingSuccessful, data);
    }
    if (type == "core") {
      scheduleElement.behaviors = [];
    }

    //scheduleElement.isToday = true;
    scheduleElement.isToday = dateIsCurrentDay(dateObj);
  }
}

// more of gavin's location tracker
function ratingSuccessful(result) {
  renderToast(result.error);
}

// opens search bar
function openSearchBar() {
  var titlebar = document.querySelector(".headerbarpages");
  titlebar.entryAnimation = "slide-from-top-animation";
  titlebar.exitAnimation = "";
  titlebar.selected = 1;
  var input = document.querySelector("paper-input.paper-typeahead-input")
  input.tabIndex = 1; // we can only focus elements with tab indexes, so we need to give our paper-input one

  // we need to set a time out here, because the dom renders funny when a focused input moves
  setTimeout(function(){ input.focus(); }, 200);
}

// closes search bad to allow interaction with other ui
function closeSearchBar() {
  var titlebar = document.querySelector(".headerbarpages");
  titlebar.exitAnimation = "slide-up-animation";
  titlebar.entryAnimation = "";
  titlebar.selected = 0;
}

// opens popup
function openPopup(title) {
  var titleSpan = document.getElementById("popupTitle");
  titleSpan.textContent = title;
  pages.entryAnimation = "slide-from-right-animation";
  pages.exitAnimation = "";
  pages.selected = 1;
}

// closes popup
function closePopup() {
  pages.entryAnimation = "";
  pages.exitAnimation = "slide-right-animation";
  pages.selected = 0;
}

// removes spaces and periods from a string
function cleanString(text) {
  text = text.toLowerCase();
  text = text.replace(/ /g, "_"); // Remove spaces
  text = text.replace(/\./g, ""); // Remove periods
  return text;
}

// checks privacy settings
function closePrivacyDialog() {
  document.getElementById("privacydialog").close();
  var share_photo = document.getElementById("initialsharephototoggle");
  var share_schedule = document.getElementById("initialsharescheduletoggle");
  sendUpdatePrivacyRequest(share_photo.checked, share_schedule.checked);
}

// shows privacy settings
function changePrivacySettings() {
  document.getElementById("privacydialogcollapse").show()
}

// waits for events and updates the ui based on the events
document.addEventListener('WebComponentsReady', function() {
  var scheduleElement = document.getElementById('mainschedule');
  scheduleElement.addEventListener("swiped", scheduleSwiped, false);
  updateMainSchedule();
  var input = document.querySelector("paper-typeahead-input")

  input.addEventListener('pt-item-confirmed', function() {
    var obj = input.inputObject;
    requestAdditionalData(obj.username, "student", renderStudent);
    openPopup(obj.name);
  });
});