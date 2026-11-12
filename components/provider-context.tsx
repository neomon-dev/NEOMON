"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

export type ProviderKind = "ollama" | "lm_studio" | "openai_compatible";

export type SessionProviderConfig = {
  kind: ProviderKind;
  endpoint: string;
  model?: string;
  apiKey?: string;
  allowLocalRuntime: boolean;
  discoveredModels: string[];
  connected: boolean;
};

type ProviderContextValue = {
  config: SessionProviderConfig | null;
  setConfig: (next: SessionProviderConfig | null) => void;
  clearConfig: () => void;
};

const ProviderContext = createContext<ProviderContextValue | undefined>(undefined);

export function ProviderSessionProvider({ children }: Readonly<{ children: ReactNode }>) {
  // Strictly in-memory React state: never persisted to localStorage or sessionStorage.
  const [config, setConfig] = useState<SessionProviderConfig | null>(null);

  return (
    <ProviderContext.Provider
      value={{
        config,
        setConfig,
        clearConfig: () => setConfig(null),
      }}
    >
      {children}
    </ProviderContext.Provider>
  );
}

export function useProviderSession(): ProviderContextValue {
  const ctx = useContext(ProviderContext);
  if (!ctx) {
    throw new Error("useProviderSession must be used within ProviderSessionProvider");
  }
  return ctx;
}
