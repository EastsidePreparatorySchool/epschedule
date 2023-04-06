// These API keys are public information
var firebaseConfig = {
  apiKey: "AIzaSyAz-4KWzckatftOp7Ws9sAebnmIQjc_5Ac",
  authDomain: "epschedule-v2.firebaseapp.com",
  databaseURL: "https://epschedule-v2.firebaseio.com",
  projectId: "epschedule-v2",
  storageBucket: "epschedule-v2.appspot.com",
  messagingSenderId: "795697214579",
  appId: "1:795697214579:web:29da422869841b742d2606",
};
firebase.initializeApp(firebaseConfig);

function microsoftLogin(postAction) {
  var provider = new firebase.auth.OAuthProvider("microsoft.com");
  provider.setCustomParameters({
    domain_hint: "eastsideprep.org",
  });
  firebase
    .auth()
    .signInWithPopup(provider)
    .then(function (result) {
      console.log(result);
      result.user.getIdToken().then(function (token) {
        document.cookie = "token=" + token;
        displayToast("Signing you in...");
        location.reload();
      });
    })
    .catch(function (error) {
      console.log(error);
      displayToast("There was a problem signing you in");
    });
}

function displayToast(text) {
  toast = document.getElementById("toast");
  toast.text = text;
  toast.show();
}
