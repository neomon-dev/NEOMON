"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { BackendStatus } from "@/components/backend-status";
import { ProviderSessionProvider } from "@/components/provider-context";
import { useAuth } from "@/lib/auth-context";

const navigation = [
  { label: "Dashboard", icon: "⌂", href: "/" },
  { label: "New investigation", icon: "+", href: "/investigations/new" },
  { label: "Autonomous research", icon: "⚡", href: "/autonomous" },
  { label: "Workspaces", icon: "👥", href: "/workspaces" },
  { label: "Peer reviews", icon: "📋", href: "/reviews" },
  { label: "Notifications", icon: "🔔", href: "/notifications" },
  { label: "Research history", icon: "↺", href: "/history" },
  { label: "Intelligence hub", icon: "❖", href: "/intelligence" },
  { label: "Knowledge graph", icon: "⌘", href: "/graph" },
  { label: "Research gaps", icon: "🎯", href: "/gaps" },
  { label: "Hypotheses", icon: "🔬", href: "/hypotheses" },
  { label: "Cross-synthesis", icon: "🔗", href: "/synthesis" },
  { label: "Contradictions", icon: "⚖", href: "/contradictions" },
  { label: "Research trends", icon: "📈", href: "/trends" },
  { label: "Quality audit", icon: "🛡", href: "/quality-audit" },
  { label: "Scientific benchmarks", icon: "📊", href: "/benchmarks" },
  { label: "Evidence library", icon: "◇", href: "/evidence" },
  { label: "Agent laboratory", icon: "◎", href: "/agents" },
  { label: "Source intelligence", icon: "◈", href: "/sources" },
  { label: "Settings", icon: "⚙", href: "/settings" },
];

export function AppShell({ children }: Readonly<{ children: ReactNode }>) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, workspaces, activeWorkspace, unreadCount, switchWorkspace, logout } = useAuth();
  const [showWorkspaceMenu, setShowWorkspaceMenu] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  return (
    <ProviderSessionProvider>
      <div className="shell">
        <aside className="sidebar">
          <Link className="brand" href="/">
            <div className="brand-mark">N</div>
            <div>
              <strong>NEOMON</strong>
              <span>Research intelligence</span>
            </div>
          </Link>
          <nav aria-label="Primary navigation">
            {navigation.map((item) => {
              const isActive =
                item.href === "/"
                  ? pathname === "/"
                  : pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  className={isActive ? "nav-item active" : "nav-item"}
                  href={item.href}
                  key={item.href}
                >
                  <span className="nav-icon">{item.icon}</span>
                  {item.label}
                  {item.href === "/notifications" && unreadCount > 0 && (
                    <span
                      style={{
                        marginLeft: "auto",
                        background: "#3b82f6",
                        color: "#fff",
                        borderRadius: "10px",
                        padding: "1px 6px",
                        fontSize: "10px",
                        fontWeight: 700,
                      }}
                    >
                      {unreadCount}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
          <div className="sidebar-footer">
            <BackendStatus />
          </div>
        </aside>
        <div className="workspace">
          {/* Top Collaborative Header Bar */}
          <header
            style={{
              height: "56px",
              background: "#080d1a",
              borderBottom: "1px solid #1a263d",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "0 28px",
              position: "sticky",
              top: 0,
              zIndex: 30,
            }}
          >
            {/* Workspace Switcher */}
            <div style={{ position: "relative" }}>
              <button
                type="button"
                onClick={() => setShowWorkspaceMenu((prev) => !prev)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  background: "#101b2f",
                  border: "1px solid #233554",
                  borderRadius: "6px",
                  padding: "6px 12px",
                  color: "#e2e8f0",
                  fontSize: "12px",
                  cursor: "pointer",
                  fontWeight: 500,
                }}
              >
                <span style={{ color: "#60a5fa" }}>👥</span>
                <span style={{ maxWidth: "200px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {activeWorkspace ? activeWorkspace.name : "Select Workspace"}
                </span>
                {activeWorkspace?.user_role && (
                  <span
                    style={{
                      background: "#1e3a5f",
                      color: "#93c5fd",
                      borderRadius: "4px",
                      padding: "1px 5px",
                      fontSize: "10px",
                      textTransform: "uppercase",
                    }}
                  >
                    {activeWorkspace.user_role}
                  </span>
                )}
                <span style={{ fontSize: "10px", color: "#64748b" }}>▼</span>
              </button>

              {showWorkspaceMenu && (
                <div
                  style={{
                    position: "absolute",
                    top: "100%",
                    left: 0,
                    marginTop: "6px",
                    background: "#0f172a",
                    border: "1px solid #334155",
                    borderRadius: "8px",
                    boxShadow: "0 10px 25px -5px rgba(0,0,0,0.5)",
                    width: "280px",
                    zIndex: 50,
                    padding: "6px",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "#64748b", padding: "6px 8px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    Switch Workspace
                  </div>
                  {workspaces.map((ws) => (
                    <button
                      key={ws.id}
                      type="button"
                      onClick={() => {
                        switchWorkspace(ws.id);
                        setShowWorkspaceMenu(false);
                      }}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        width: "100%",
                        padding: "8px 10px",
                        textAlign: "left",
                        background: activeWorkspace?.id === ws.id ? "#1e293b" : "transparent",
                        border: "none",
                        borderRadius: "5px",
                        color: activeWorkspace?.id === ws.id ? "#38bdf8" : "#cbd5e1",
                        fontSize: "12px",
                        cursor: "pointer",
                      }}
                    >
                      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{ws.name}</span>
                      {ws.user_role && (
                        <span style={{ fontSize: "10px", color: "#94a3b8", textTransform: "uppercase" }}>
                          {ws.user_role}
                        </span>
                      )}
                    </button>
                  ))}
                  <div style={{ borderTop: "1px solid #1e293b", margin: "6px 0" }} />
                  <Link
                    href="/workspaces"
                    onClick={() => setShowWorkspaceMenu(false)}
                    style={{
                      display: "block",
                      padding: "6px 8px",
                      fontSize: "12px",
                      color: "#60a5fa",
                      textDecoration: "none",
                      textAlign: "center",
                    }}
                  >
                    + Manage & Create Workspaces
                  </Link>
                </div>
              )}
            </div>

            {/* Right section: Notification bell + User avatar */}
            <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
              {/* Notification Bell */}
              <Link
                href="/notifications"
                style={{
                  position: "relative",
                  color: "#cbd5e1",
                  fontSize: "16px",
                  textDecoration: "none",
                  padding: "4px 8px",
                  borderRadius: "6px",
                }}
              >
                🔔
                {unreadCount > 0 && (
                  <span
                    style={{
                      position: "absolute",
                      top: "0px",
                      right: "2px",
                      background: "#ef4444",
                      color: "#fff",
                      borderRadius: "50%",
                      width: "16px",
                      height: "16px",
                      fontSize: "10px",
                      display: "grid",
                      placeItems: "center",
                      fontWeight: 700,
                    }}
                  >
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                )}
              </Link>

              {/* User menu */}
              {user ? (
                <div style={{ position: "relative" }}>
                  <button
                    type="button"
                    onClick={() => setShowUserMenu((prev) => !prev)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      background: "transparent",
                      border: "none",
                      color: "#e2e8f0",
                      fontSize: "12px",
                      cursor: "pointer",
                    }}
                  >
                    <div
                      style={{
                        width: "28px",
                        height: "28px",
                        borderRadius: "50%",
                        background: "#2563eb",
                        color: "#fff",
                        display: "grid",
                        placeItems: "center",
                        fontWeight: 600,
                        fontSize: "12px",
                      }}
                    >
                      {user.display_name ? user.display_name[0].toUpperCase() : "U"}
                    </div>
                    <span style={{ fontWeight: 500 }}>{user.display_name}</span>
                    <span style={{ fontSize: "10px", color: "#64748b" }}>▼</span>
                  </button>

                  {showUserMenu && (
                    <div
                      style={{
                        position: "absolute",
                        top: "100%",
                        right: 0,
                        marginTop: "6px",
                        background: "#0f172a",
                        border: "1px solid #334155",
                        borderRadius: "8px",
                        boxShadow: "0 10px 25px -5px rgba(0,0,0,0.5)",
                        width: "200px",
                        zIndex: 50,
                        padding: "6px",
                      }}
                    >
                      <div style={{ padding: "8px 10px", borderBottom: "1px solid #1e293b" }}>
                        <div style={{ fontSize: "12px", fontWeight: 600, color: "#f8fafc" }}>{user.display_name}</div>
                        <div style={{ fontSize: "11px", color: "#94a3b8", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {user.email}
                        </div>
                      </div>
                      <Link
                        href="/profile"
                        onClick={() => setShowUserMenu(false)}
                        style={{
                          display: "block",
                          padding: "8px 10px",
                          fontSize: "12px",
                          color: "#cbd5e1",
                          textDecoration: "none",
                          borderRadius: "4px",
                        }}
                      >
                        Profile & Settings
                      </Link>
                      <button
                        type="button"
                        onClick={async () => {
                          setShowUserMenu(false);
                          await logout();
                          router.push("/login");
                        }}
                        style={{
                          width: "100%",
                          textAlign: "left",
                          padding: "8px 10px",
                          fontSize: "12px",
                          color: "#f87171",
                          background: "transparent",
                          border: "none",
                          cursor: "pointer",
                          borderRadius: "4px",
                        }}
                      >
                        Sign out
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ display: "flex", gap: "8px" }}>
                  <Link
                    href="/login"
                    style={{
                      padding: "5px 12px",
                      fontSize: "12px",
                      color: "#94a3b8",
                      textDecoration: "none",
                      border: "1px solid #334155",
                      borderRadius: "6px",
                    }}
                  >
                    Sign in
                  </Link>
                  <Link
                    href="/register"
                    style={{
                      padding: "5px 12px",
                      fontSize: "12px",
                      color: "#fff",
                      background: "#2563eb",
                      textDecoration: "none",
                      borderRadius: "6px",
                      fontWeight: 500,
                    }}
                  >
                    Register
                  </Link>
                </div>
              )}
            </div>
          </header>

          <main>{children}</main>
        </div>
      </div>
    </ProviderSessionProvider>
  );
}
