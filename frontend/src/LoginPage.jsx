import React, { useState } from 'react';
import { initializeApp } from 'firebase/app';
import { getAuth, OAuthProvider, signInWithPopup } from 'firebase/auth';

const firebaseConfig = {
  apiKey: 'AIzaSyAz-4KWzckatftOp7Ws9sAebnmIQjc_5Ac',
  authDomain: 'epschedule-v2.firebaseapp.com',
  projectId: 'epschedule-v2',
  storageBucket: 'epschedule-v2.appspot.com',
  messagingSenderId: '795697214579',
  appId: '1:795697214579:web:29da422869841b742d2606',
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

export default function LoginPage() {
  const [toast, setToast] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleLogin() {
    setLoading(true);
    try {
      const provider = new OAuthProvider('microsoft.com');
      provider.setCustomParameters({ domain_hint: 'eastsideprep.org' });
      const result = await signInWithPopup(auth, provider);
      const token = await result.user.getIdToken();
      document.cookie = 'token=' + token;
      setToast('Signing you in...');
      setTimeout(() => location.reload(), 1000);
    } catch (err) {
      console.error(err);
      setToast('There was a problem signing you in');
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="card">
        <div className="image-container">
          <img src="/static/images/epslogo.jpg" alt="EPS Logo" />
        </div>
        <h1>EPSchedule</h1>
        <p className="copy">The easiest way to keep track of your classes and classmates.</p>
        <button className="login-button" onClick={handleLogin} disabled={loading}>
          {loading ? 'Signing in...' : 'SIGN IN'}
        </button>
      </div>
      {toast && <div className="login-toast">{toast}</div>}
    </div>
  );
}
