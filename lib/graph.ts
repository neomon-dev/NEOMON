import type { Edge, Node } from "@xyflow/react";

export type GraphNodeType =
  | "investigation"
  | "research_question"
  | "claim"
  | "evidence"
  | "document"
  | "source"
  | "agent_argument"
  | "adjudication_decision"
  | "research_gap"
  | "hypothesis"
  | "contradiction"
  | "cross_investigation"
  | "research_trend"
  | "autonomous_workflow"
  | "research_cycle"
  | "research_action";

export type GraphNodeView = {
  id: string;
  entity_id: string;
  type: GraphNodeType;
  label: string;
  description: string;
  investigation_id: string;
  status: string;
  missing_provenance: string[];
  has_hidden_neighbors: boolean;
  metadata: Record<string, unknown>;
};

export type GraphEdgeView = {
  id: string;
  source: string;
  target: string;
  relationship_type: string;
  label: string;
  classification?: string | null;
  explanation?: string | null;
};

export type GraphTotalCounts = {
  claims: number;
  evidence: number;
  documents: number;
  sources: number;
  arguments: number;
  decisions: number;
  research_gaps?: number;
  hypotheses?: number;
  contradictions?: number;
  cross_relationships?: number;
  trends?: number;
  workflows?: number;
  cycles?: number;
  actions?: number;
};

export type InvestigationGraphResponse = {
  investigation_id?: string | null;
  investigation_question?: string | null;
  investigation_status?: string | null;
  nodes: GraphNodeView[];
  edges: GraphEdgeView[];
  truncated: boolean;
  total_counts: GraphTotalCounts;
  node_type_counts: Record<string, number>;
  relationship_type_counts: Record<string, number>;
  empty_reason?: string | null;
};

export type KnowledgeNodeData = GraphNodeView & {
  isSearchMatch: boolean;
  isDimmed: boolean;
  isBranchCollapsed: boolean;
  hiddenDescendantCount: number;
};

export const NODE_TYPE_ORDER: GraphNodeType[] = [
  "investigation",
  "research_question",
  "autonomous_workflow",
  "research_cycle",
  "research_action",
  "claim",
  "adjudication_decision",
  "agent_argument",
  "evidence",
  "document",
  "source",
  "research_gap",
  "hypothesis",
  "contradiction",
  "cross_investigation",
  "research_trend",
];

export const NODE_TYPE_META: Record<
  GraphNodeType,
  { label: string; shortLabel: string; tier: number; accent: string; bg: string }
> = {
  investigation: {
    label: "Investigation",
    shortLabel: "INV",
    tier: 0,
    accent: "#4b9dff",
    bg: "#10203a",
  },
  research_question: {
    label: "Research question",
    shortLabel: "QUESTION",
    tier: 1,
    accent: "#8d78ff",
    bg: "#191836",
  },
  claim: {
    label: "Claim",
    shortLabel: "CLAIM",
    tier: 2,
    accent: "#6baaff",
    bg: "#11223d",
  },
  adjudication_decision: {
    label: "Adjudication decision",
    shortLabel: "DECISION",
    tier: 3,
    accent: "#55d5a0",
    bg: "#102925",
  },
  agent_argument: {
    label: "Agent argument",
    shortLabel: "ARGUMENT",
    tier: 3,
    accent: "#a58fff",
    bg: "#1c1938",
  },
  evidence: {
    label: "Evidence passage",
    shortLabel: "EVIDENCE",
    tier: 4,
    accent: "#55d5a0",
    bg: "#102624",
  },
  document: {
    label: "Document",
    shortLabel: "DOCUMENT",
    tier: 5,
    accent: "#6cd4ff",
    bg: "#102433",
  },
  source: {
    label: "Source / publication",
    shortLabel: "SOURCE",
    tier: 6,
    accent: "#47c7a0",
    bg: "#112424",
  },
  research_gap: {
    label: "Research gap",
    shortLabel: "GAP",
    tier: 3,
    accent: "#f97316",
    bg: "#2b1810",
  },
  hypothesis: {
    label: "Research hypothesis",
    shortLabel: "HYP",
    tier: 2,
    accent: "#a855f7",
    bg: "#261338",
  },
  contradiction: {
    label: "Contradiction",
    shortLabel: "CONTRA",
    tier: 3,
    accent: "#ef4444",
    bg: "#3b1219",
  },
  cross_investigation: {
    label: "Cross-Investigation",
    shortLabel: "SYNTH",
    tier: 1,
    accent: "#06b6d4",
    bg: "#0e2a38",
  },
  research_trend: {
    label: "Research trend",
    shortLabel: "TREND",
    tier: 1,
    accent: "#eab308",
    bg: "#382e0e",
  },
  autonomous_workflow: {
    label: "Autonomous workflow",
    shortLabel: "WORKFLOW",
    tier: 0,
    accent: "#f59e0b",
    bg: "#2d2008",
  },
  research_cycle: {
    label: "Research cycle",
    shortLabel: "CYCLE",
    tier: 1,
    accent: "#38bdf8",
    bg: "#0c2536",
  },
  research_action: {
    label: "Research action",
    shortLabel: "ACTION",
    tier: 2,
    accent: "#ec4899",
    bg: "#311025",
  },
};

export function edgeStrokeFor(relationshipType: string): {
  stroke: string;
  strokeDasharray?: string;
} {
  switch (relationshipType) {
    case "supports":
      return { stroke: "#55d5a0" };
    case "contradicts":
      return { stroke: "#e27d8f" };
    case "mitigates":
      return { stroke: "#b388ff", strokeDasharray: "4 2" };
    case "contextualizes":
      return { stroke: "#4b9dff", strokeDasharray: "6 3" };
    case "has_gap":
      return { stroke: "#f97316", strokeDasharray: "4 2" };
    case "affects":
      return { stroke: "#fb923c", strokeDasharray: "3 3" };
    case "hypothesizes":
      return { stroke: "#a855f7", strokeDasharray: "4 2" };
    case "supports_hypothesis":
      return { stroke: "#55d5a0", strokeDasharray: "3 3" };
    case "challenges":
      return { stroke: "#ef4444" };
    case "synthesizes_with":
      return { stroke: "#06b6d4", strokeDasharray: "5 3" };
    case "tracks_trend":
      return { stroke: "#eab308", strokeDasharray: "4 2" };
    case "investigates":
      return { stroke: "#f59e0b", strokeDasharray: "5 3" };
    case "executes_cycle":
      return { stroke: "#38bdf8" };
    case "performs_action":
      return { stroke: "#ec4899" };
    case "targets_claim":
      return { stroke: "#6baaff", strokeDasharray: "4 2" };
    case "targets_gap":
      return { stroke: "#f97316", strokeDasharray: "4 2" };
    case "targets_hypothesis":
      return { stroke: "#a855f7", strokeDasharray: "4 2" };
    case "methodological_limitation":
      return { stroke: "#e6bd67", strokeDasharray: "6 3" };
    case "source_criticism":
      return { stroke: "#f29f67", strokeDasharray: "3 3" };
    case "temporal_qualification":
      return { stroke: "#8d78ff", strokeDasharray: "3 3" };
    case "extracted_from_source":
      return { stroke: "#e6bd67", strokeDasharray: "4 4" };
    default:
      return { stroke: "#486086" };
  }
}

export function nodeAccentFor(node: GraphNodeView): string {
  if (node.type === "evidence") {
    if (node.status === "contradicting") return "#e27d8f";
    if (node.status === "mitigating") return "#b388ff";
    if (node.status === "methodological_limitation") return "#e6bd67";
    if (node.status === "contextual") return "#4b9dff";
    if (node.status === "insufficient") return "#718096";
    return "#55d5a0";
  }
  if (node.type === "adjudication_decision") {
    if (node.status === "contradictory") return "#e27d8f";
    if (node.status === "insufficient_evidence") return "#e6bd67";
    return "#55d5a0";
  }
  return NODE_TYPE_META[node.type]?.accent ?? "#4b9dff";
}

export function mergeGraphResponses(
  existing: InvestigationGraphResponse,
  incoming: InvestigationGraphResponse,
): InvestigationGraphResponse {
  const nodeMap = new Map<string, GraphNodeView>();
  for (const node of existing.nodes) nodeMap.set(node.id, node);
  for (const node of incoming.nodes) nodeMap.set(node.id, node);

  const edgeMap = new Map<string, GraphEdgeView>();
  for (const edge of existing.edges) edgeMap.set(edge.id, edge);
  for (const edge of incoming.edges) edgeMap.set(edge.id, edge);

  const nodes = Array.from(nodeMap.values());
  const validIds = new Set(nodes.map((node) => node.id));
  const edges = Array.from(edgeMap.values()).filter(
    (edge) => validIds.has(edge.source) && validIds.has(edge.target),
  );

  return {
    ...incoming,
    nodes,
    edges,
    truncated:
      nodes.filter((n) => n.type === "claim").length < incoming.total_counts.claims ||
      nodes.filter((n) => n.type === "evidence").length < incoming.total_counts.evidence ||
      nodes.filter((n) => n.type === "source").length < incoming.total_counts.sources,
  };
}

export function computeVisibleSubgraph(
  nodes: GraphNodeView[],
  edges: GraphEdgeView[],
  options: {
    activeNodeTypes: Set<GraphNodeType>;
    relationshipFilter: string;
    collapsedBranchIds: Set<string>;
  },
): {
  visibleNodes: GraphNodeView[];
  visibleEdges: GraphEdgeView[];
  hiddenDescendantCounts: Map<string, number>;
} {
  const baseNodes = nodes.filter((node) => options.activeNodeTypes.has(node.type));
  const baseIds = new Set(baseNodes.map((node) => node.id));
  const baseEdges = edges.filter(
    (edge) =>
      baseIds.has(edge.source) &&
      baseIds.has(edge.target) &&
      (options.relationshipFilter === "all" || edge.relationship_type === options.relationshipFilter),
  );

  // Build adjacency for cycle-safe branch collapse from collapsed roots
  const outgoing = new Map<string, string[]>();
  const incoming = new Map<string, string[]>();
  for (const edge of baseEdges) {
    if (!outgoing.has(edge.source)) outgoing.set(edge.source, []);
    outgoing.get(edge.source)!.push(edge.target);
    if (!incoming.has(edge.target)) incoming.set(edge.target, []);
    incoming.get(edge.target)!.push(edge.source);
  }

  const hiddenIds = new Set<string>();
  const hiddenDescendantCounts = new Map<string, number>();

  for (const collapsedRoot of options.collapsedBranchIds) {
    if (!baseIds.has(collapsedRoot)) continue;
    const queue = [...(outgoing.get(collapsedRoot) ?? [])];
    const visited = new Set<string>();
    let hiddenForRoot = 0;

    while (queue.length > 0) {
      const current = queue.shift()!;
      if (visited.has(current) || current === collapsedRoot) continue;
      visited.add(current);

      const parents = incoming.get(current) ?? [];
      const allParentsCollapsedOrHidden =
        parents.length > 0 &&
        parents.every(
          (parent) =>
            parent === collapsedRoot ||
            options.collapsedBranchIds.has(parent) ||
            hiddenIds.has(parent) ||
            visited.has(parent),
        );
      if (!allParentsCollapsedOrHidden) continue;
      if (!hiddenIds.has(current)) {
        hiddenIds.add(current);
        hiddenForRoot += 1;
      }
      for (const next of outgoing.get(current) ?? []) {
        if (!visited.has(next)) queue.push(next);
      }
    }
    hiddenDescendantCounts.set(collapsedRoot, hiddenForRoot);
  }

  const visibleNodes = baseNodes.filter((node) => !hiddenIds.has(node.id));
  const visibleIds = new Set(visibleNodes.map((node) => node.id));
  const visibleEdges = baseEdges.filter(
    (edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target),
  );

  return { visibleNodes, visibleEdges, hiddenDescendantCounts };
}

export function buildFlowElements(
  visibleNodes: GraphNodeView[],
  visibleEdges: GraphEdgeView[],
  options: {
    searchQuery: string;
    collapsedBranchIds: Set<string>;
    hiddenDescendantCounts: Map<string, number>;
    previousPositions?: Map<string, { x: number; y: number }>;
  },
): {
  flowNodes: Array<Node<KnowledgeNodeData>>;
  flowEdges: Edge[];
  matchedNodeIds: string[];
} {
  const query = options.searchQuery.trim().toLowerCase();
  const matchedNodeIds: string[] = [];

  const buckets = new Map<number, GraphNodeView[]>();
  for (const node of visibleNodes) {
    const tier = NODE_TYPE_META[node.type]?.tier ?? 3;
    if (!buckets.has(tier)) buckets.set(tier, []);
    buckets.get(tier)!.push(node);
  }

  // Compute deterministic horizontal hierarchical layout
  const tierKeys = Array.from(buckets.keys()).sort((a, b) => a - b);
  const maxRows = Math.max(1, ...Array.from(buckets.values()).map((items) => items.length));
  const columnSpacing = 330;
  const rowSpacing = 148;
  const totalHeight = maxRows * rowSpacing;

  const computedPositions = new Map<string, { x: number; y: number }>();
  for (const tier of tierKeys) {
    const group = buckets.get(tier)!;
    const groupHeight = group.length * rowSpacing;
    const startY = Math.max(24, (totalHeight - groupHeight) / 2);
    group.forEach((node, idx) => {
      computedPositions.set(node.id, {
        x: 40 + tier * columnSpacing,
        y: Math.round(startY + idx * rowSpacing),
      });
    });
  }

  const flowNodes: Array<Node<KnowledgeNodeData>> = visibleNodes.map((node) => {
    const isMatch =
      query.length > 0 &&
      (node.label.toLowerCase().includes(query) ||
        node.description.toLowerCase().includes(query) ||
        node.status.toLowerCase().includes(query));
    if (isMatch) matchedNodeIds.push(node.id);

    const preserved = options.previousPositions?.get(node.id);
    const position = preserved ?? computedPositions.get(node.id) ?? { x: 40, y: 40 };

    return {
      id: node.id,
      type: "knowledgeNode",
      position,
      data: {
        ...node,
        isSearchMatch: isMatch,
        isDimmed: query.length > 0 && !isMatch,
        isBranchCollapsed: options.collapsedBranchIds.has(node.id),
        hiddenDescendantCount: options.hiddenDescendantCounts.get(node.id) ?? 0,
      },
    };
  });

  const flowEdges: Edge[] = visibleEdges.map((edge) => {
    const style = edgeStrokeFor(edge.relationship_type);
    return {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.label,
      type: "smoothstep",
      animated:
        edge.relationship_type === "supports" ||
        edge.relationship_type === "contradicts" ||
        edge.relationship_type === "extracted_from_source",
      style: {
        stroke: style.stroke,
        strokeWidth: edge.relationship_type === "supports" || edge.relationship_type === "contradicts" ? 2.4 : 1.6,
        strokeDasharray: style.strokeDasharray,
        filter: edge.relationship_type === "contradicts" ? "drop-shadow(0 0 4px rgba(255, 82, 119, 0.5))" : edge.relationship_type === "supports" ? "drop-shadow(0 0 4px rgba(53, 224, 177, 0.4))" : undefined,
      },
      labelStyle: {
        fill: "#b8c7df",
        fontSize: 10,
        fontWeight: 500,
      },
      labelBgStyle: {
        fill: "#0b111e",
        fillOpacity: 0.9,
      },
      data: edge,
    };
  });

  return { flowNodes, flowEdges, matchedNodeIds };
}
