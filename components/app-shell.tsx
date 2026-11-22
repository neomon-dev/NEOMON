"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { BackendStatus } from "@/components/backend-status";
import { DotLens } from "@/components/dot-lens";
import { ProviderSessionProvider } from "@/components/provider-context";
import { useAuth } from "@/lib/auth-context";

interface NavItem {
  label: string;
  icon: string;
  href: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const navSections: NavSection[] = [
  {
    title: "Core Research",
    items: [
      { label: "Dashboard", icon: "⌂", href: "/" },
      { label: "New investigation", icon: "+", href: "/investigations/new" },
      { label: "Autonomous research", icon: "⚡", href: "/autonomous" },
      { label: "Research history", icon: "↺", href: "/history" },
    ],
  },
  {
    title: "Evidence & Knowledge",
    items: [
      { label: "Intelligence hub", icon: "❖", href: "/intelligence" },
      { label: "Evidence library", icon: "◇", href: "/evidence" },
      { label: "Source intelligence", icon: "◈", href: "/sources" },
      { label: "Knowledge graph", icon: "⌘", href: "/graph" },
    ],
  },
  {
    title: "Analysis & Synthesis",
    items: [
      { label: "Research gaps", icon: "🎯", href: "/gaps" },
      { label: "Hypotheses", icon: "🔬", href: "/hypotheses" },
      { label: "Cross-synthesis", icon: "🔗", href: "/synthesis" },
      { label: "Contradictions", icon: "⚖", href: "/contradictions" },
      { label: "Research trends", icon: "📈", href: "/trends" },
    ],
  },
  {
    title: "Verification & Benchmarks",
    items: [
      { label: "Quality audit", icon: "🛡", href: "/quality-audit" },
      { label: "Scientific benchmarks", icon: "📊", href: "/benchmarks" },
      { label: "Agent laboratory", icon: "◎", href: "/agents" },
    ],
  },
  {
    title: "Collaboration & System",
    items: [
      { label: "Workspaces", icon: "👥", href: "/workspaces" },
      { label: "Peer reviews", icon: "📋", href: "/reviews" },
      { label: "Notifications", icon: "🔔", href: "/notifications" },
      { label: "Settings", icon: "⚙", href: "/settings" },
    ],
  },
];

export function AppShell({ children }: Readonly<{ children: ReactNode }>) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, workspaces, activeWorkspace, unreadCount, switchWorkspace, logout } = useAuth();
  const [showWorkspaceMenu, setShowWorkspaceMenu] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <ProviderSessionProvider>
      <div className="shell">
        <DotLens
          background="#06111F"
          baseColor="#082F49"
          midColor="#647BFF"
          accentColor="#36C5DE"
          density={34}
          dotSize={78}
          reach={20}
          minSize={10}
          hover={100}
          speed={32}
        />
        <aside className="sidebar">
          <Link className="brand" href="/" title="NEOMON — RESEARCH BEYOND THE SURFACE.">
            <div className="brand-symbol-container">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/brand/neomon-symbol.png"
                alt="NEOMON"
                width={36}
                height={36}
                className="brand-symbol-img"
              />
            </div>
            <div>
              <strong>NEOMON</strong>
              <span className="brand-slogan">RESEARCH BEYOND THE SURFACE.</span>
            </div>
          </Link>
          <nav aria-label="Primary navigation">
            {navSections.map((section) => (
              <div key={section.title} className="nav-section" style={{ marginBottom: "8px" }}>
                <div className="nav-section-title">{section.title}</div>
                {section.items.map((item) => {
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
              </div>
            ))}
          </nav>
          <div className="sidebar-footer">
            <BackendStatus />
          </div>
        </aside>
        <div className="workspace">
          {/* Top Collaborative Header Bar */}
          <header className="global-header">
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              {/* Mobile Menu Toggle Button */}
              <button
                type="button"
                className="mobile-only mobile-menu-toggle-btn"
                onClick={() => setMobileMenuOpen(true)}
                aria-label="Open mobile navigation"
                style={{
                  background: "rgba(15, 23, 42, 0.6)",
                  border: "1px solid var(--border)",
                  color: "#f8fafc",
                  padding: "6px 10px",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontSize: "15px",
                }}
              >
                ☰
              </button>

              {/* Workspace Switcher */}
              <div style={{ position: "relative" }}>
                <button
                  type="button"
                  className="workspace-switcher-btn"
                  onClick={() => setShowWorkspaceMenu((prev) => !prev)}
                >
                  <span style={{ color: "#38bdf8" }}>👥</span>
                  <span style={{ maxWidth: "200px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {activeWorkspace ? activeWorkspace.name : "Select Workspace"}
                  </span>
                  {activeWorkspace?.user_role && (
                    <span className="workspace-badge-role">
                      {activeWorkspace.user_role}
                    </span>
                  )}
                  <span style={{ fontSize: "10px", color: "var(--muted)" }}>▼</span>
                </button>

              {showWorkspaceMenu && (
                <div className="workspace-dropdown-menu">
                  <div className="workspace-dropdown-title">
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
                      className={activeWorkspace?.id === ws.id ? "workspace-dropdown-item active" : "workspace-dropdown-item"}
                    >
                      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{ws.name}</span>
                      {ws.user_role && (
                        <span style={{ fontSize: "10px", color: "#94a3b8", textTransform: "uppercase" }}>
                          {ws.user_role}
                        </span>
                      )}
                    </button>
                  ))}
                  <div style={{ borderTop: "1px solid var(--border)", margin: "6px 0" }} />
                  <Link
                    href="/workspaces"
                    onClick={() => setShowWorkspaceMenu(false)}
                    style={{
                      display: "block",
                      padding: "7px 8px",
                      fontSize: "12px",
                      color: "#38bdf8",
                      textDecoration: "none",
                      textAlign: "center",
                      fontWeight: 500,
                    }}
                  >
                    + Manage & Create Workspaces
                  </Link>
                </div>
              )}
            </div>
            </div>

            {/* Right section: Notification bell + User avatar */}
            <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
              {/* Notification Bell */}
              <Link
                href="/notifications"
                className="header-bell-btn"
                aria-label="Notifications"
              >
                🔔
                {unreadCount > 0 && (
                  <span className="header-bell-badge">
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                )}
              </Link>

              {/* User menu */}
              {user ? (
                <div style={{ position: "relative" }}>
                  <button
                    type="button"
                    className="user-menu-btn"
                    onClick={() => setShowUserMenu((prev) => !prev)}
                  >
                    <div className="user-avatar-circle">
                      {user.display_name ? user.display_name[0].toUpperCase() : "U"}
                    </div>
                    <span style={{ fontWeight: 500 }}>{user.display_name}</span>
                    <span style={{ fontSize: "10px", color: "var(--muted)" }}>▼</span>
                  </button>

                  {showUserMenu && (
                    <div className="user-dropdown-menu">
                      <div style={{ padding: "8px 10px", borderBottom: "1px solid var(--border)" }}>
                        <div style={{ fontSize: "12px", fontWeight: 600, color: "#f8fafc" }}>{user.display_name}</div>
                        <div style={{ fontSize: "11px", color: "var(--muted)", overflow: "hidden", textOverflow: "ellipsis" }}>
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
                          transition: "background 0.15s ease",
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
                      padding: "6px 14px",
                      fontSize: "12px",
                      color: "#94a3b8",
                      textDecoration: "none",
                      border: "1px solid var(--border)",
                      borderRadius: "6px",
                      transition: "all 0.15s ease",
                    }}
                  >
                    Sign in
                  </Link>
                  <Link
                    href="/register"
                    className="primary-button"
                    style={{
                      padding: "6px 14px",
                      fontSize: "12px",
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

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div
            className="mobile-drawer-backdrop"
            onClick={() => setMobileMenuOpen(false)}
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(0, 0, 0, 0.75)",
              backdropFilter: "blur(6px)",
              zIndex: 100,
              display: "flex",
            }}
          >
            <div
              className="mobile-drawer-sheet"
              onClick={(e) => e.stopPropagation()}
              style={{
                width: "280px",
                maxWidth: "85vw",
                height: "100%",
                background: "#070b14",
                borderRight: "1px solid var(--border)",
                padding: "20px 16px",
                display: "flex",
                flexDirection: "column",
                overflowY: "auto",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", paddingBottom: "12px", borderBottom: "1px solid var(--border)" }}>
                <Link className="brand" href="/" onClick={() => setMobileMenuOpen(false)} title="NEOMON — RESEARCH BEYOND THE SURFACE." style={{ margin: 0, padding: 0, border: "none" }}>
                  <div className="brand-symbol-container" style={{ width: "32px", height: "32px" }}>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src="/brand/neomon-symbol.png"
                      alt="NEOMON"
                      width={32}
                      height={32}
                      className="brand-symbol-img"
                    />
                  </div>
                  <div>
                    <strong>NEOMON</strong>
                    <span className="brand-slogan">RESEARCH BEYOND THE SURFACE.</span>
                  </div>
                </Link>
                <button
                  type="button"
                  onClick={() => setMobileMenuOpen(false)}
                  style={{ background: "none", border: "none", color: "var(--muted)", fontSize: "20px", cursor: "pointer", padding: "4px 8px" }}
                >
                  ✕
                </button>
              </div>

              <nav aria-label="Mobile navigation" style={{ flex: 1 }}>
                {navSections.map((section) => (
                  <div key={section.title} className="nav-section" style={{ marginBottom: "12px" }}>
                    <div className="nav-section-title">{section.title}</div>
                    {section.items.map((item) => {
                      const isActive =
                        item.href === "/"
                          ? pathname === "/"
                          : pathname === item.href || pathname.startsWith(`${item.href}/`);
                      return (
                        <Link
                          className={isActive ? "nav-item active" : "nav-item"}
                          href={item.href}
                          key={item.href}
                          onClick={() => setMobileMenuOpen(false)}
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
                  </div>
                ))}
              </nav>

              <div style={{ marginTop: "auto", paddingTop: "12px", borderTop: "1px solid var(--border)" }}>
                <BackendStatus />
              </div>
            </div>
          </div>
        )}
      </div>
    </ProviderSessionProvider>
  );
}
