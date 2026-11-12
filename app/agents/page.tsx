import { Suspense } from "react";
import { AgentObservatory } from "@/components/agent-observatory";

export default function AgentsPage() {
  return (
    <Suspense
      fallback={
        <div className="content">
          <div className="panel empty-state">
            <p className="muted">Loading Agent Observatory...</p>
          </div>
        </div>
      }
    >
      <AgentObservatory />
    </Suspense>
  );
}
