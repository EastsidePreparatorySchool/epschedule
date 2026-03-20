import React, { useState, useEffect } from "react";
import { updatePrivacy, getPrivacy } from "../utils/api";
import { useAppContext } from "../context/AppContext";

export default function SettingsDialog({
  sharePhoto: initialSharePhoto,
  onClose,
}) {
  const [sharePhoto, setSharePhoto] = useState(initialSharePhoto);
  const { showToast } = useAppContext();

  useEffect(() => {
    getPrivacy()
      .then((data) => setSharePhoto(data.share_photo))
      .catch(() => {});
  }, []);

  async function handleOK() {
    try {
      await updatePrivacy(sharePhoto);
      showToast("Settings updated!");
    } catch (err) {
      showToast(err.message || "Error updating settings");
    }
    onClose();
  }

  return (
    <div
      className="dialog-overlay"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="dialog">
        <h2 className="settings-title">Settings</h2>
        <hr className="settings-divider" />
        <h3 className="privacypaneltitle">Privacy</h3>
        <div className="settings-row">
          <label className="settings-label">
            <span>Show other EPS students my photo</span>
            <input
              type="checkbox"
              checked={sharePhoto}
              onChange={(e) => setSharePhoto(e.target.checked)}
            />
          </label>
          <p className="settings-note">
            Note that you will still be able to see your own photo
          </p>
        </div>
        <button className="settings-ok-btn" onClick={handleOK}>
          OK
        </button>
      </div>
    </div>
  );
}
