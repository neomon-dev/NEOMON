"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  listNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  getNotificationPreferences,
  updateNotificationPreferences,
  NotificationItem,
} from "@/lib/collaboration";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function NotificationsPage() {
  const { refreshAuth } = useAuth();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUnauthenticated, setIsUnauthenticated] = useState(false);

  // Preferences
  const [inAppEnabled, setInAppEnabled] = useState(true);
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [savingPrefs, setSavingPrefs] = useState(false);

  const loadNotifications = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setIsUnauthenticated(false);
      const [notifs, prefs] = await Promise.all([
        listNotifications(50, unreadOnly),
        getNotificationPreferences().catch(() => ({ email_notifications_enabled: true, in_app_notifications_enabled: true })),
      ]);
      setNotifications(notifs);
      setInAppEnabled(prefs.in_app_notifications_enabled);
      setEmailEnabled(prefs.email_notifications_enabled);
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 401) {
        setIsUnauthenticated(true);
        setNotifications([]);
        setError(null);
      } else {
        setError(err instanceof Error ? err.message : "Failed to load notifications.");
      }
    } finally {
      setLoading(false);
    }
  }, [unreadOnly]);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  const handleMarkRead = async (id: string) => {
    try {
      await markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      await refreshAuth();
    } catch (err: unknown) {
      console.error("Failed to mark notification as read", err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      await refreshAuth();
    } catch (err: unknown) {
      console.error("Failed to mark all as read", err);
    }
  };

  const handleTogglePref = async (email: boolean, inApp: boolean) => {
    setSavingPrefs(true);
    try {
      await updateNotificationPreferences(email, inApp);
      setEmailEnabled(email);
      setInAppEnabled(inApp);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to update preferences.");
    } finally {
      setSavingPrefs(false);
    }
  };

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div style={{ padding: "36px 40px", maxWidth: "900px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "24px" }}>
        <div>
          <h1 style={{ fontSize: "24px", fontWeight: 700, color: "#f8fafc", margin: "0 0 6px" }}>
            Notifications & Research Alerts
          </h1>
          <p style={{ color: "#94a3b8", fontSize: "13px", margin: 0 }}>
            Mentions, review requests, evidence annotations, and workspace invitations.
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          {unreadCount > 0 && (
            <button
              type="button"
              onClick={handleMarkAllRead}
              style={{
                padding: "8px 14px",
                background: "#1e293b",
                color: "#cbd5e1",
                border: "1px solid #334155",
                borderRadius: "6px",
                fontSize: "12px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              ✓ Mark All Read
            </button>
          )}
          <button
            type="button"
            onClick={loadNotifications}
            disabled={loading}
            style={{
              padding: "8px 14px",
              background: "#2563eb",
              color: "#fff",
              border: "none",
              borderRadius: "6px",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: "8px", borderBottom: "1px solid #1a263d", marginBottom: "24px", paddingBottom: "8px" }}>
        <button
          type="button"
          onClick={() => setUnreadOnly(false)}
          style={{
            padding: "6px 14px",
            background: !unreadOnly ? "#2563eb" : "transparent",
            color: !unreadOnly ? "#fff" : "#94a3b8",
            border: "none",
            borderRadius: "6px",
            fontSize: "13px",
            fontWeight: 500,
            cursor: "pointer",
          }}
        >
          All Notifications
        </button>
        <button
          type="button"
          onClick={() => setUnreadOnly(true)}
          style={{
            padding: "6px 14px",
            background: unreadOnly ? "#2563eb" : "transparent",
            color: unreadOnly ? "#fff" : "#94a3b8",
            border: "none",
            borderRadius: "6px",
            fontSize: "13px",
            fontWeight: 500,
            cursor: "pointer",
          }}
        >
          Unread Only {unreadCount > 0 && `(${unreadCount})`}
        </button>
      </div>

      {isUnauthenticated && (
        <div
          style={{
            background: "rgba(14, 165, 233, 0.1)",
            border: "1px solid rgba(56, 189, 248, 0.3)",
            borderRadius: "8px",
            padding: "16px 20px",
            marginBottom: "20px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
            <div>
              <p style={{ margin: "0 0 4px", fontSize: "14px", fontWeight: 600, color: "#f0f9ff" }}>
                Guest Session — Authentication Required
              </p>
              <p style={{ margin: 0, fontSize: "12px", color: "#93c5fd" }}>
                Sign in to view your research notifications, review requests, and workspace activity alerts.
              </p>
            </div>
            <Link
              href="/login"
              style={{
                padding: "8px 16px",
                background: "#0284c7",
                color: "#fff",
                borderRadius: "6px",
                fontSize: "12px",
                fontWeight: 600,
                textDecoration: "none",
              }}
            >
              Sign In
            </Link>
          </div>
        </div>
      )}

      {error && (
        <div style={{ background: "#450a0a", border: "1px solid #991b1b", color: "#fca5a5", padding: "12px 16px", borderRadius: "8px", marginBottom: "20px", fontSize: "13px" }}>
          {error}
        </div>
      )}

      {/* List */}
      {loading && notifications.length === 0 ? (
        <div style={{ padding: "40px", color: "#94a3b8", textAlign: "center" }}>
          Loading notifications...
        </div>
      ) : notifications.length === 0 ? (
        <div style={{ background: "#0f172a", border: "1px dashed #1e293b", padding: "48px 24px", textAlign: "center", borderRadius: "10px" }}>
          <h3 style={{ fontSize: "15px", color: "#94a3b8", margin: "0 0 6px" }}>No Notifications</h3>
          <p style={{ color: "#64748b", fontSize: "13px", margin: 0 }}>
            {unreadOnly ? "You have no unread notifications." : "You have no notifications yet."}
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginBottom: "36px" }}>
          {notifications.map((notif) => {
            const eventIcon =
              notif.event_type === "mention"
                ? "@"
                : notif.event_type.includes("review")
                ? "🛡️"
                : notif.event_type.includes("invitation")
                ? "✉️"
                : "💬";

            return (
              <div
                key={notif.id}
                style={{
                  background: notif.is_read ? "#0f172a" : "#0f233f",
                  border: `1px solid ${notif.is_read ? "#1e293b" : "#1e40af"}`,
                  borderRadius: "8px",
                  padding: "16px 20px",
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "14px",
                }}
              >
                <div
                  style={{
                    width: "32px",
                    height: "32px",
                    borderRadius: "50%",
                    background: notif.is_read ? "#1e293b" : "#1d4ed8",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "14px",
                    flexShrink: 0,
                    color: "#f8fafc",
                  }}
                >
                  {eventIcon}
                </div>

                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                    <h3 style={{ fontSize: "14px", fontWeight: 600, color: notif.is_read ? "#e2e8f0" : "#ffffff", margin: 0 }}>
                      {notif.title}
                    </h3>
                    <span style={{ color: "#64748b", fontSize: "11px" }}>
                      {notif.created_at ? new Date(notif.created_at).toLocaleString() : ""}
                    </span>
                  </div>
                  <p style={{ color: "#94a3b8", fontSize: "13px", margin: "0 0 8px" }}>
                    {notif.message}
                  </p>

                  <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                    {notif.link_url && (
                      <Link
                        href={notif.link_url}
                        style={{ color: "#38bdf8", fontSize: "12px", textDecoration: "none", fontWeight: 500 }}
                      >
                        View Details →
                      </Link>
                    )}
                    {!notif.is_read && (
                      <button
                        type="button"
                        onClick={() => handleMarkRead(notif.id)}
                        style={{
                          background: "none",
                          border: "none",
                          color: "#64748b",
                          fontSize: "12px",
                          cursor: "pointer",
                          padding: 0,
                          textDecoration: "underline",
                        }}
                      >
                        Mark as read
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Preferences Section */}
      <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "10px", padding: "20px 24px" }}>
        <h3 style={{ fontSize: "15px", fontWeight: 600, color: "#f8fafc", margin: "0 0 12px" }}>
          Notification Delivery Preferences
        </h3>
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          <label style={{ display: "flex", alignItems: "center", gap: "10px", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={inAppEnabled}
              disabled={savingPrefs}
              onChange={(e) => handleTogglePref(emailEnabled, e.target.checked)}
            />
            <span style={{ color: "#cbd5e1", fontSize: "13px" }}>In-App Notifications</span>
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: "10px", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={emailEnabled}
              disabled={savingPrefs}
              onChange={(e) => handleTogglePref(e.target.checked, inAppEnabled)}
            />
            <span style={{ color: "#cbd5e1", fontSize: "13px" }}>Email Digest / Instant Alerts</span>
          </label>
        </div>
      </div>
    </div>
  );
}
