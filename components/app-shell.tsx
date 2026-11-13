"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { BackendStatus } from "@/components/backend-status";
import { ProviderSessionProvider } from "@/components/provider-context";

const navigation = [
  { label: "Dashboard", icon: "⌂", href: "/" },
  { label: "New investigation", icon: "+", href: "/investigations/new" },
  { label: "Research history", icon: "↺", href: "/history" },
  { label: "Intelligence hub", icon: "❖", href: "/intelligence" },
  { label: "Knowledge graph", icon: "⌘", href: "/graph" },
  { label: "Research gaps", icon: "⚡", href: "/gaps" },
  { label: "Hypotheses", icon: "🔬", href: "/hypotheses" },
  { label: "Cross-synthesis", icon: "🔗", href: "/synthesis" },
  { label: "Contradictions", icon: "⚖", href: "/contradictions" },
  { label: "Research trends", icon: "📈", href: "/trends" },
  { label: "Quality audit", icon: "🛡", href: "/quality-audit" },
  { label: "Evidence library", icon: "◇", href: "/evidence" },
  { label: "Agent laboratory", icon: "◎", href: "/agents" },
  { label: "Source intelligence", icon: "◈", href: "/sources" },
  { label: "Settings", icon: "⚙", href: "/settings" },
];

export function AppShell({ children }: Readonly<{ children: ReactNode }>) {
  const pathname = usePathname();

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
                </Link>
              );
            })}
          </nav>
          <div className="sidebar-footer">
            <BackendStatus />
          </div>
        </aside>
        <div className="workspace">{children}</div>
      </div>
    </ProviderSessionProvider>
  );
}
