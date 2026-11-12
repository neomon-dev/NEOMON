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
        borderColor: selected ? "#eef4ff" : accent,
        background: meta.bg,
      }}
    >
      <Handle position={Position.Left} style={{ background: accent, borderColor: "#090d16" }} type="target" />
      <div className="kg-node-header">
        <span className="kg-node-type" style={{ color: accent }}>
          {meta.shortLabel}
        </span>
        <span className="kg-node-status">{data.status.replace(/_/g, " ")}</span>
      </div>
      <div className="kg-node-title">{data.label}</div>
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
