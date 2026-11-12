import { Suspense } from "react";
import { KnowledgeGraphWorkspace } from "@/components/knowledge-graph-workspace";

export default function GraphPage() {
  return (
    <Suspense
      fallback={
        <div className="content">
          <div className="panel empty-state">
            <p className="muted">Loading Knowledge Graph...</p>
          </div>
        </div>
      }
    >
      <KnowledgeGraphWorkspace />
    </Suspense>
  );
}
