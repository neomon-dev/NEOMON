import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AppShell } from "@/components/app-shell";
import { AuthProvider } from "@/lib/auth-context";
import { CinematicIntro } from "@/components/cinematic-intro";
import "./globals.css";

export const metadata: Metadata = {
  title: "NEOMON | Research Intelligence",
  description: "Every claim is questioned. Every source is traced. Every conclusion is earned. Research beyond the surface.",
  icons: {
    icon: [
      { url: "/brand/neomon-favicon.svg", type: "image/svg+xml" },
    ],
    apple: [
      { url: "/brand/neomon-app-icon.png", sizes: "512x512", type: "image/png" },
    ],
  },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/brand/neomon-favicon.svg" type="image/svg+xml" />
        <link rel="apple-touch-icon" href="/brand/neomon-app-icon.png" />
      </head>
      <body>
        <CinematicIntro />
        <AuthProvider>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  );
}
