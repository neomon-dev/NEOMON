"use client";

import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { NODE_TYPE_META, nodeAccentFor, type KnowledgeNodeData } from "@/lib/graph";

type KnowledgeFlowNode = Node<KnowledgeNodeData, "knowledgeNode">;

export function KnowledgeGraphNode({ data, selected }: NodeProps<KnowledgeFlowNode>) {
  const meta = NODE_TYPE_META[data.type];
  const accent = nodeAccentFor(data);
  const missingCount = data.missing_provenance?.length ?? 0;

  return (
    <div
      aria-label={`${meta.label}: ${data.label}`}
      className={`kg-node${selected ? " kg-node-selected" : ""}${data.isSearchMatch ? " kg-node-match" : ""}${data.isDimmed ? " kg-node-dimmed" : ""}`}
      style={{
        borderColor: selected ? "#38bdf8" : accent,
        background: meta.bg,
        boxShadow: selected ? `0 0 24px -2px ${accent}, 0 0 0 1px #fff` : `0 4px 16px rgba(0, 0, 0, 0.45)`,
      }}
    >
      <div className="hud-corner-tl" style={{ borderColor: accent }} />
      <div className="hud-corner-tr" style={{ borderColor: accent }} />
      <div className="hud-corner-bl" style={{ borderColor: accent }} />
      <div className="hud-corner-br" style={{ borderColor: accent }} />
      <Handle position={Position.Left} style={{ background: accent, borderColor: "#050914" }} type="target" />
      <div className="kg-node-header">
        <span className="kg-node-type" style={{ color: accent, display: "flex", alignItems: "center", gap: "5px" }}>
          <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: accent, boxShadow: `0 0 6px ${accent}` }} />
          {meta.shortLabel}
        </span>
        <span className="kg-node-status" style={{ fontFamily: "monospace", fontSize: "9px" }}>
          {data.status.replace(/_/g, " ")}
        </span>
      </div>
      <div className="kg-node-title" style={{ fontSize: "12px", lineHeight: 1.45, fontWeight: 600, color: "#ECF5FF" }}>{data.label}</div>
      {(missingCount > 0 || data.has_hidden_neighbors || data.isBranchCollapsed) && (
        <div className="kg-node-flags">
          {missingCount > 0 && (
            <span className="kg-flag kg-flag-missing">
              {data.missing_provenance[0].replace(/_/g, " ")}
            </span>
          )}
          {data.has_hidden_neighbors && <span className="kg-flag kg-flag-expand">+ expandable</span>}
          {data.isBranchCollapsed && (
            <span className="kg-flag kg-flag-collapsed">
              collapsed ({data.hiddenDescendantCount})
            </span>
          )}
        </div>
      )}
      <Handle position={Position.Right} style={{ background: accent, borderColor: "#090d16" }} type="source" />
    </div>
  );
}
