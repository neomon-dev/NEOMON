"use client";

import { useEffect, useState } from "react";
import { requestJson } from "../lib/api";

type BackendState = {
  status: "loading" | "online" | "offline";
  demoMode: boolean;
  agentCount: number;
  message?: string;
};

export function BackendStatus() {
  const [state, setState] = useState<BackendState>({
    status: "loading",
    demoMode: false,
    agentCount: 0,
  });

  useEffect(() => {
    let active = true;
    async function loadStatus() {
      try {
        const [health, agents] = await Promise.all([
          requestJson<{ demo_mode: boolean }>("/health", { cache: "no-store" }),
          requestJson<unknown[]>("/agents", { cache: "no-store" }),
        ]);
        if (active) {
          setState({
            status: "online",
            demoMode: health.demo_mode,
            agentCount: agents.length,
          });
        }
      } catch {
        if (active) {
          setState({
            status: "offline",
            demoMode: false,
            agentCount: 0,
            message: "Start the FastAPI service to connect.",
          });
        }
      }
    }
    void loadStatus();
    return () => {
      active = false;
    };
  }, []);

  const label =
    state.status === "loading"
      ? "Connecting to backend..."
      : state.status === "online"
        ? state.demoMode
          ? `Demo mode · ${state.agentCount} agents ready`
          : `Backend online · ${state.agentCount} agents ready`
        : state.message;

  return (
    <span className={`backend-status ${state.status}`}>
      <i className="status-dot" />
      {label}
    </span>
  );
}
