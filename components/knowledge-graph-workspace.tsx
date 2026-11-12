"use client";

import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type Node,
  type NodeChange,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { GraphDetailPanel } from "@/components/graph-detail-panel";
import { KnowledgeGraphNode } from "@/components/knowledge-graph-node";
import { requestJson } from "@/lib/api";
import {
  NODE_TYPE_META,
  NODE_TYPE_ORDER,
  buildFlowElements,
  computeVisibleSubgraph,
  mergeGraphResponses,
  type GraphEdgeView,
  type GraphNodeType,
  type GraphNodeView,
  type InvestigationGraphResponse,
  type KnowledgeNodeData,
} from "@/lib/graph";
import type { InvestigationSummary } from "@/lib/workspace";

const nodeTypes = { knowledgeNode: KnowledgeGraphNode };

function GraphCanvasInner() {
  const searchParams = useSearchParams();
  const initialInvId = searchParams.get("investigation_id") ?? "";
  const { fitView, setCenter } = useReactFlow();

  const [investigations, setInvestigations] = useState<InvestigationSummary[]>([]);
  const [investigationId, setInvestigationId] = useState<string>(initialInvId);
  const [graphData, setGraphData] = useState<InvestigationGraphResponse | null>(null);
  const [userPositions, setUserPositions] = useState<Map<string, { x: number; y: number }>>(
    () => new Map(),
  );

  const [searchQuery, setSearchQuery] = useState("");
  const [activeNodeTypes, setActiveNodeTypes] = useState<Set<GraphNodeType>>(
    () => new Set(NODE_TYPE_ORDER),
  );
  const [relationshipFilter, setRelationshipFilter] = useState("all");
  const [collapsedBranchIds, setCollapsedBranchIds] = useState<Set<string>>(() => new Set());
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [expandingNodeId, setExpandingNodeId] = useState<string | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    requestJson<InvestigationSummary[]>("/research/investigations")
      .then((rows) => {
        if (!active) return;
        setInvestigations(rows);
        setInvestigationId((prev) => prev || rows[0]?.id || "");
      })
      .catch(() => {
        // Primary graph request surfaces connectivity failures.
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    async function loadInvestigationGraph() {
      setLoading(true);
      const params = new URLSearchParams();
      if (investigationId) params.set("investigation_id", investigationId);
      try {
        const response = await requestJson<InvestigationGraphResponse>(`/research/graph?${params.toString()}`);
        if (!active) return;
        setGraphData(response);
        setError("");
        if (response.investigation_id && !investigationId) {
          setInvestigationId(response.investigation_id);
        }
        setSelectedNodeId(null);
        setSelectedEdgeId(null);
        setCollapsedBranchIds(new Set());
        setUserPositions(new Map());
      } catch (reason) {
        if (!active) return;
        setError(reason instanceof Error ? reason.message : "Could not load knowledge graph.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadInvestigationGraph();
    return () => {
      active = false;
    };
  }, [investigationId]);

  const handleLoadFullGraph = useCallback(async () => {
    if (!graphData?.investigation_id) return;
    setLoading(true);
    const params = new URLSearchParams({
      investigation_id: graphData.investigation_id,
      expand_all: "true",
      max_nodes: "600",
    });
    try {
      const response = await requestJson<InvestigationGraphResponse>(`/research/graph?${params.toString()}`);
      setGraphData(response);
      setError("");
      setSelectedNodeId(null);
      setSelectedEdgeId(null);
      setCollapsedBranchIds(new Set());
      setUserPositions(new Map());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load full knowledge graph.");
    } finally {
      setLoading(false);
    }
  }, [graphData]);

  const { visibleNodes, visibleEdges, hiddenDescendantCounts } = useMemo(() => {
    if (!graphData) {
      return {
        visibleNodes: [] as GraphNodeView[],
        visibleEdges: [] as GraphEdgeView[],
        hiddenDescendantCounts: new Map<string, number>(),
      };
    }
    return computeVisibleSubgraph(graphData.nodes, graphData.edges, {
      activeNodeTypes,
      relationshipFilter,
      collapsedBranchIds,
    });
  }, [graphData, activeNodeTypes, relationshipFilter, collapsedBranchIds]);

  const { flowNodes, flowEdges, matchedNodeIds } = useMemo(() => {
    const built = buildFlowElements(visibleNodes, visibleEdges, {
      searchQuery,
      collapsedBranchIds,
      hiddenDescendantCounts,
      previousPositions: userPositions,
    });
    return {
      flowNodes: built.flowNodes,
      flowEdges: built.flowEdges,
      matchedNodeIds: built.matchedNodeIds,
    };
  }, [visibleNodes, visibleEdges, searchQuery, collapsedBranchIds, hiddenDescendantCounts, userPositions]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setSelectedNodeId(null);
        setSelectedEdgeId(null);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const handleNodesChange = useCallback(
    (changes: NodeChange<Node<KnowledgeNodeData>>[]) => {
      let hasPositionChanges = false;
      const nextPositions = new Map(userPositions);
      for (const change of changes) {
        if (change.type === "position" && change.position) {
          nextPositions.set(change.id, change.position);
          hasPositionChanges = true;
        }
      }
      if (hasPositionChanges) {
        setUserPositions(nextPositions);
      }
    },
    [userPositions],
  );

  const handleExpandNode = useCallback(
    async (nodeId: string) => {
      if (!graphData?.investigation_id) return;
      setExpandingNodeId(nodeId);
      setCollapsedBranchIds((prev) => {
        if (!prev.has(nodeId)) return prev;
        const next = new Set(prev);
        next.delete(nodeId);
        return next;
      });
      try {
        const params = new URLSearchParams({
          investigation_id: graphData.investigation_id,
          focus_node_id: nodeId,
          max_nodes: "250",
        });
        const expansion = await requestJson<InvestigationGraphResponse>(`/research/graph?${params.toString()}`);
        setGraphData((prev) => (prev ? mergeGraphResponses(prev, expansion) : expansion));
        setError("");
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "Could not expand connected nodes.");
      } finally {
        setExpandingNodeId(null);
      }
    },
    [graphData],
  );

  const handleToggleCollapse = useCallback((nodeId: string) => {
    setCollapsedBranchIds((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  }, []);

  const handleResetLayout = useCallback(() => {
    setUserPositions(new Map());
    setCollapsedBranchIds(new Set());
    window.requestAnimationFrame(() => {
      void fitView({ padding: 0.16, duration: 250 });
    });
  }, [fitView]);

  const handleFocusSearchMatch = useCallback(() => {
    if (matchedNodeIds.length === 0) return;
    const matchId = matchedNodeIds[0];
    setSelectedNodeId(matchId);
    setSelectedEdgeId(null);
    const target = flowNodes.find((item) => item.id === matchId);
    if (target) {
      void setCenter(target.position.x + 120, target.position.y + 45, { zoom: 1.05, duration: 250 });
    }
  }, [matchedNodeIds, flowNodes, setCenter]);

  const toggleNodeType = (type: GraphNodeType) => {
    setActiveNodeTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type) && next.size > 1) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  };

  const nodeMap = useMemo(() => {
    const map = new Map<string, GraphNodeView>();
    for (const node of graphData?.nodes ?? []) {
      map.set(node.id, node);
    }
    return map;
  }, [graphData]);

  const selectedNode = selectedNodeId ? nodeMap.get(selectedNodeId) ?? null : null;
  const selectedEdge = selectedEdgeId
    ? (graphData?.edges ?? []).find((edge) => edge.id === selectedEdgeId) ?? null
    : null;

  return (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">Evidence Intelligence Workspace</p>
          <h1>Knowledge Graph</h1>
        </div>
        <div className="analysis-actions">
          {graphData?.investigation_id && (
            <Link className="outline-button compact-button" href={`/investigations/${graphData.investigation_id}`}>
              Open investigation
            </Link>
          )}
          <Link className="primary-button" href="/investigations/new">
            + New investigation
          </Link>
        </div>
      </header>

      <div className="content">
        <div className="metric-grid">
          <article className="metric-card">
            <span className="metric-label">Visible nodes</span>
            <strong>{flowNodes.length}</strong>
            <span className="metric-detail">
              Total persisted claims: {graphData?.total_counts.claims ?? 0} · evidence: {graphData?.total_counts.evidence ?? 0}
            </span>
          </article>
          <article className="metric-card">
            <span className="metric-label">Persisted edges</span>
            <strong>{flowEdges.length}</strong>
            <span className="metric-detail">Zero fabricated links or similarity guesses</span>
          </article>
          <article className="metric-card">
            <span className="metric-label">Search highlights</span>
            <strong>{matchedNodeIds.length}</strong>
            <span className="metric-detail">Matches across visible graph labels & claims</span>
          </article>
          <article className="metric-card">
            <span className="metric-label">Graph coverage</span>
            <strong>{graphData?.truncated ? "Bounded slice" : "Complete"}</strong>
            <span className="metric-detail">
              {graphData?.total_counts.sources ?? 0} sources · {graphData?.total_counts.documents ?? 0} documents
            </span>
          </article>
        </div>

        <section className="panel" style={{ marginTop: 18 }}>
          <div className="workspace-toolbar">
            <select
              aria-label="Select investigation for knowledge graph"
              className="filter-select"
              value={investigationId}
              onChange={(event) => setInvestigationId(event.target.value)}
            >
              {investigations.length === 0 && <option value="">No investigations yet</option>}
              {investigations.map((inv) => (
                <option key={inv.id} value={inv.id}>
                  {inv.question.slice(0, 62)}
                  {inv.question.length > 62 ? "…" : ""} ({inv.source_count} src · {inv.evidence_count} ev)
                </option>
              ))}
            </select>

            <input
              aria-label="Search and highlight graph nodes"
              className="filter-input"
              placeholder="Search nodes (press Enter to jump to first match)..."
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  handleFocusSearchMatch();
                }
              }}
            />

            <select
              aria-label="Filter by relationship type"
              className="filter-select"
              value={relationshipFilter}
              onChange={(event) => setRelationshipFilter(event.target.value)}
            >
              <option value="all">All persisted relationships</option>
              <option value="supports">Supports</option>
              <option value="contradicts">Contradicts</option>
              <option value="contextualizes">Contextualizes / Qualifies</option>
              <option value="methodological_limitation">Methodological limitation</option>
              <option value="source_criticism">Source criticism</option>
              <option value="temporal_qualification">Temporal qualification</option>
              <option value="evidenced_in">Evidence → Document</option>
              <option value="published_by">Document → Source</option>
              <option value="adjudicated_by">Claim → Adjudication</option>
            </select>

            <button
              className="outline-button compact-button"
              type="button"
              onClick={() => void fitView({ padding: 0.16, duration: 250 })}
            >
              Fit to screen
            </button>
            <button className="outline-button compact-button" type="button" onClick={handleResetLayout}>
              Reset layout
            </button>
            {graphData?.truncated && graphData.investigation_id && (
              <button
                className="primary-button compact-button"
                type="button"
                onClick={() => void handleLoadFullGraph()}
              >
                Load full graph
              </button>
            )}
          </div>

          <div className="kg-chip-bar" role="group" aria-label="Filter graph node types">
            {NODE_TYPE_ORDER.map((type) => {
              const meta = NODE_TYPE_META[type];
              const active = activeNodeTypes.has(type);
              const count = graphData?.node_type_counts[type] ?? 0;
              return (
                <button
                  key={type}
                  type="button"
                  className={`kg-filter-chip${active ? " active" : ""}`}
                  style={{ borderColor: active ? meta.accent : undefined }}
                  onClick={() => toggleNodeType(type)}
                >
                  <span className="kg-dot" style={{ background: meta.accent }} />
                  {meta.label} ({count})
                </button>
              );
            })}
          </div>

          {error && <p className="connection-result error dashboard-error">{error}</p>}

          {loading ? (
            <div className="empty-state">
              <p className="muted">Loading persisted evidence knowledge graph...</p>
            </div>
          ) : flowNodes.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">⌘</div>
              <h4>No knowledge graph nodes to display</h4>
              <p>{graphData?.empty_reason ?? "Start a research investigation or adjust active filters."}</p>
            </div>
          ) : (
            <div className="workspace-split kg-split">
              <div className="kg-canvas-wrap">
                <ReactFlow
                  edges={flowEdges}
                  fitView
                  fitViewOptions={{ padding: 0.16 }}
                  maxZoom={2}
                  minZoom={0.2}
                  nodes={flowNodes}
                  nodeTypes={nodeTypes}
                  onlyRenderVisibleElements
                  onEdgeClick={(_event, edge: Edge) => {
                    setSelectedEdgeId(edge.id);
                    setSelectedNodeId(null);
                  }}
                  onNodeClick={(_event, node) => {
                    setSelectedNodeId(node.id);
                    setSelectedEdgeId(null);
                  }}
                  onNodesChange={handleNodesChange}
                  onPaneClick={() => {
                    setSelectedNodeId(null);
                    setSelectedEdgeId(null);
                  }}
                >
                  <Background color="#1d2b44" gap={22} size={1} />
                  <Controls />
                  <MiniMap
                    maskColor="#090d16aa"
                    nodeColor={(node) => {
                      const data = node.data as KnowledgeNodeData | undefined;
                      return data ? NODE_TYPE_META[data.type]?.accent ?? "#4b9dff" : "#4b9dff";
                    }}
                    pannable
                    style={{ background: "#0b111e", border: "1px solid #223049" }}
                    zoomable
                  />
                </ReactFlow>
              </div>

              <GraphDetailPanel
                expandingNodeId={expandingNodeId}
                isCollapsed={selectedNode ? collapsedBranchIds.has(selectedNode.id) : false}
                nodeMap={nodeMap}
                selectedEdge={selectedEdge}
                selectedNode={selectedNode}
                onClearSelection={() => {
                  setSelectedNodeId(null);
                  setSelectedEdgeId(null);
                }}
                onExpandNode={(nodeId) => void handleExpandNode(nodeId)}
                onSelectNodeById={(nodeId) => {
                  if (nodeMap.has(nodeId)) {
                    setSelectedNodeId(nodeId);
                    setSelectedEdgeId(null);
                  } else {
                    void handleExpandNode(nodeId).then(() => {
                      setSelectedNodeId(nodeId);
                      setSelectedEdgeId(null);
                    });
                  }
                }}
                onToggleCollapse={handleToggleCollapse}
              />
            </div>
          )}
        </section>
      </div>
    </>
  );
}

export function KnowledgeGraphWorkspace() {
  return (
    <ReactFlowProvider>
      <GraphCanvasInner />
    </ReactFlowProvider>
  );
}
