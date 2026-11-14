"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import {
  updateProfile,
  changePassword,
  getNotificationPreferences,
  updateNotificationPreferences,
} from "@/lib/collaboration";

export default function ProfilePage() {
  const { user, refreshAuth } = useAuth();
  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [emailNotifs, setEmailNotifs] = useState(true);
  const [inAppNotifs, setInAppNotifs] = useState(true);

  const [profileMsg, setProfileMsg] = useState<string | null>(null);
  const [profileErr, setProfileErr] = useState<string | null>(null);
  const [pwMsg, setPwMsg] = useState<string | null>(null);
  const [pwErr, setPwErr] = useState<string | null>(null);
  const [prefMsg, setPrefMsg] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setDisplayName(user.display_name || "");
      setBio(user.bio || "");
    }
    getNotificationPreferences().then((p) => {
      if (p) {
        setEmailNotifs(p.email_notifications_enabled);
        setInAppNotifs(p.in_app_notifications_enabled);
      }
    });
  }, [user]);

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileMsg(null);
    setProfileErr(null);
    try {
      await updateProfile(displayName, bio);
      await refreshAuth();
      setProfileMsg("Profile updated successfully.");
    } catch (err: unknown) {
      setProfileErr(err instanceof Error ? err.message : "Failed to update profile.");
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwMsg(null);
    setPwErr(null);
    try {
      await changePassword(oldPassword, newPassword);
      setPwMsg("Password updated successfully.");
      setOldPassword("");
      setNewPassword("");
    } catch (err: unknown) {
      setPwErr(err instanceof Error ? err.message : "Failed to change password.");
    }
  };

  const handleUpdatePreferences = async () => {
    try {
      await updateNotificationPreferences(emailNotifs, inAppNotifs);
      setPrefMsg("Preferences saved.");
      setTimeout(() => setPrefMsg(null), 3000);
    } catch {
      setPrefMsg("Failed to save preferences.");
    }
  };

  return (
    <div style={{ padding: "40px 32px", maxWidth: "800px", margin: "0 auto" }}>
      <div style={{ marginBottom: "32px" }}>
        <h1 style={{ fontSize: "24px", fontWeight: 700, color: "#f8fafc", margin: "0 0 6px" }}>
          User Profile & Settings
        </h1>
        <p style={{ color: "#94a3b8", fontSize: "13px", margin: 0 }}>
          Manage your account credentials, research profile, and notification settings.
        </p>
      </div>

      <div style={{ display: "grid", gap: "24px" }}>
        {/* Profile Card */}
        <div style={{ background: "#0d1527", border: "1px solid #1e293b", borderRadius: "10px", padding: "24px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: 600, color: "#f8fafc", margin: "0 0 16px" }}>
            Profile Information
          </h2>
          {profileMsg && <div style={{ color: "#34d399", fontSize: "13px", marginBottom: "12px" }}>{profileMsg}</div>}
          {profileErr && <div style={{ color: "#f87171", fontSize: "13px", marginBottom: "12px" }}>{profileErr}</div>}
          <form onSubmit={handleUpdateProfile} style={{ display: "grid", gap: "14px" }}>
            <div>
              <label htmlFor="user-email-static" style={{ display: "block", fontSize: "12px", color: "#94a3b8", marginBottom: "4px" }}>
                Email address (read-only)
              </label>
              <input
                id="user-email-static"
                type="text"
                disabled
                value={user?.email || ""}
                style={{ width: "100%", padding: "8px 12px", background: "#080d1a", border: "1px solid #1e293b", color: "#64748b", borderRadius: "6px", fontSize: "13px", boxSizing: "border-box" }}
              />
            </div>
            <div>
              <label htmlFor="prof-name-input" style={{ display: "block", fontSize: "12px", color: "#cbd5e1", marginBottom: "4px" }}>
                Display Name
              </label>
              <input
                id="prof-name-input"
                type="text"
                required
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                style={{ width: "100%", padding: "8px 12px", background: "#080d1a", border: "1px solid #334155", color: "#f8fafc", borderRadius: "6px", fontSize: "13px", boxSizing: "border-box" }}
              />
            </div>
            <div>
              <label htmlFor="prof-bio-input" style={{ display: "block", fontSize: "12px", color: "#cbd5e1", marginBottom: "4px" }}>
                Research Bio
              </label>
              <textarea
                id="prof-bio-input"
                rows={3}
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                style={{ width: "100%", padding: "8px 12px", background: "#080d1a", border: "1px solid #334155", color: "#f8fafc", borderRadius: "6px", fontSize: "13px", resize: "vertical", boxSizing: "border-box" }}
              />
            </div>
            <div>
              <button
                type="submit"
                style={{ padding: "8px 16px", background: "#2563eb", color: "#fff", border: "none", borderRadius: "6px", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}
              >
                Save Profile
              </button>
            </div>
          </form>
        </div>

        {/* Change Password Card */}
        <div style={{ background: "#0d1527", border: "1px solid #1e293b", borderRadius: "10px", padding: "24px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: 600, color: "#f8fafc", margin: "0 0 16px" }}>
            Change Password
          </h2>
          {pwMsg && <div style={{ color: "#34d399", fontSize: "13px", marginBottom: "12px" }}>{pwMsg}</div>}
          {pwErr && <div style={{ color: "#f87171", fontSize: "13px", marginBottom: "12px" }}>{pwErr}</div>}
          <form onSubmit={handleChangePassword} style={{ display: "grid", gap: "14px" }}>
            <div>
              <label htmlFor="curr-pw-input" style={{ display: "block", fontSize: "12px", color: "#cbd5e1", marginBottom: "4px" }}>
                Current Password
              </label>
              <input
                id="curr-pw-input"
                type="password"
                required
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                style={{ width: "100%", padding: "8px 12px", background: "#080d1a", border: "1px solid #334155", color: "#f8fafc", borderRadius: "6px", fontSize: "13px", boxSizing: "border-box" }}
              />
            </div>
            <div>
              <label htmlFor="new-pw-input" style={{ display: "block", fontSize: "12px", color: "#cbd5e1", marginBottom: "4px" }}>
                New Password (min. 8 characters)
              </label>
              <input
                id="new-pw-input"
                type="password"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                style={{ width: "100%", padding: "8px 12px", background: "#080d1a", border: "1px solid #334155", color: "#f8fafc", borderRadius: "6px", fontSize: "13px", boxSizing: "border-box" }}
              />
            </div>
            <div>
              <button
                type="submit"
                style={{ padding: "8px 16px", background: "#334155", color: "#fff", border: "none", borderRadius: "6px", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}
              >
                Update Password
              </button>
            </div>
          </form>
        </div>

        {/* Notifications Card */}
        <div style={{ background: "#0d1527", border: "1px solid #1e293b", borderRadius: "10px", padding: "24px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: 600, color: "#f8fafc", margin: "0 0 16px" }}>
            Notification Preferences
          </h2>
          {prefMsg && <div style={{ color: "#38bdf8", fontSize: "13px", marginBottom: "12px" }}>{prefMsg}</div>}
          <div style={{ display: "grid", gap: "12px" }}>
            <label style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px", color: "#cbd5e1", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={inAppNotifs}
                onChange={(e) => setInAppNotifs(e.target.checked)}
              />
              Enable in-app notifications (mentions, comments, reviews, invitations)
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px", color: "#cbd5e1", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={emailNotifs}
                onChange={(e) => setEmailNotifs(e.target.checked)}
              />
              Enable email notifications for urgent review requests
            </label>
            <div style={{ marginTop: "8px" }}>
              <button
                type="button"
                onClick={handleUpdatePreferences}
                style={{ padding: "8px 16px", background: "#2563eb", color: "#fff", border: "none", borderRadius: "6px", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}
              >
                Save Preferences
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
