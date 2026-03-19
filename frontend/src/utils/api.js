export async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP error ${res.status}`);
  return res.json();
}

export async function postForm(url, data = {}) {
  const formData = new FormData();
  Object.entries(data).forEach(([k, v]) => formData.append(k, v));
  const res = await fetch(url, { method: 'POST', body: formData });
  if (!res.ok) {
    const json = await res.json().catch(() => ({}));
    throw new Error(json.error || `HTTP error ${res.status}`);
  }
  return res.json();
}

export async function logout() {
  return postForm('/logout');
}

export async function updatePrivacy(sharePhoto) {
  return postForm('/privacy', { share_photo: sharePhoto });
}

export async function getPrivacy() {
  return fetchJSON('/privacy');
}

export async function getClassData(period, termId) {
  return fetchJSON(`/class/${period.toLowerCase()}?term_id=${termId}`);
}

export async function searchPeople(query) {
  return fetchJSON(`/search/${encodeURIComponent(query)}`);
}

export async function getStudentData(username) {
  return fetchJSON(`/student/${username}`);
}
