# Feature Specification: Interactive Knowledge Graph Explorer

## 1. Feature Overview
The **Interactive Knowledge Graph Explorer** (`/graph`) provides a 2D interactive canvas powered by React Flow (`@xyflow/react`). It models the complete epistemic network of a research workspace, visualizing **16 distinct node types** (investigations, research questions, autonomous workflows, cycles, actions, claims, adjudications, agent arguments, evidence passages, documents, sources, research gaps, hypotheses, contradictions, cross-investigations, and research trends) connected by **10 typed edge relationships** with real-time search, category filtering, layout algorithms, and a slide-out Traceability Inspector.

## 2. Purpose and Problem Solved
Linear scientific text fails to convey complex interdependencies: how a single paper supports multiple claims across distinct investigations, or how a single contradictory finding invalidates an entire chain of reasoning. The Knowledge Graph solves this by:
- Unifying all scientific entities and relationships into an interactive, visual topology.
- Enabling instant visual fact-checking from high-level synthesis down to the exact source sentence.
- Visually distinguishing supporting evidence (green edges) from contradictory evidence (red dashed arcs).
- Providing flexible graph layout algorithms (Force-Directed, Hierarchical Tree, Radial Cluster, Circular).

## 3. Where Users Access It
- **Dedicated Route**: `/graph` (Knowledge Graph Explorer).
- **In-Investigation**: Knowledge Graph sub-tab on `/investigations/[id]`.
- **Navigation**: "Knowledge graph" link in the primary sidebar.

## 4. Step-by-Step User Workflow
1. Navigate to `/graph`.
2. Inspect the **Knowledge Graph Stats Banner**:
   - Total visible nodes.
   - Total persisted edges (strictly zero fabricated links or similarity guesses).
   - Search highlights count.
   - Graph coverage metrics (sources and documents mapped).
3. Select an investigation from the top dropdown or select **"All investigations"** to explore cross-inquiry links.
4. Interact with the Canvas:
   - **Pan & Zoom**: Scroll to zoom, click and drag to pan across the network.
   - **Node Type Filters**: Toggle any of the 16 node types at the top (e.g. show only Claims and Evidence).
   - **Relationship Filter**: Filter edges by type (`Supports`, `Contradicts`, `Contextualizes`, `Evidence → Document`, `Document → Source`).
   - **Search & Highlight**: Enter a term in the search box; matching nodes highlight in real time, and pressing Enter centers the viewport on the first match.
   - **Layout Switcher**: Toggle between Organic Force-Directed, Hierarchical Directed Tree, Radial Cluster, and Circular.
   - **Canvas Controls**: Click **"Fit to screen"** to auto-center or **"Reset layout"** to restore default positions.
5. Inspect Nodes:
   - Click any node on the canvas to open the **Traceability Inspector** slide-out drawer.
   - Review node label, metadata, confidence score, source URL, DOI, and connected neighboring nodes.

## 5. How the Feature Works Internally
1. When `/graph` loads or an investigation is selected, the client requests:
   `GET /api/v1/research/graph?investigation_id=<UUID>` (or without ID for workspace-wide graph).
2. The backend `app.research.graph_service` queries database tables and projects entities into a deterministic `KnowledgeGraphResponse`:
   - Nodes contain `id`, `type`, `label`, `entity_id`, and `metadata`.
   - Edges contain `id`, `source`, `target`, `relationship_type`, and `metadata`.
3. Client-side layout engine (`lib/graph.ts`):
   - **Force-Directed**: Runs an iterative D3-force simulation to position nodes based on attraction and repulsion.
   - **Hierarchical**: Uses a topological sort layered layout (Investigation → Claims → Evidence → Sources).
   - **Radial**: Arranges root nodes centrally with satellite evidence orbiting their parent claims.
4. Custom Node Renderer (`components/knowledge-graph-node.tsx`):
   - Renders distinct iconography, color coding, and verification badges based on node type.

## 6. Relevant Frontend Pages and Components
- `app/graph/page.tsx`: Full-screen graph page container.
- `components/knowledge-graph-workspace.tsx`: React Flow canvas wrapper, search toolbar, and layout controls.
- `components/knowledge-graph-node.tsx`: Custom React Flow node component with status indicators.
- `components/graph-detail-panel.tsx`: Slide-out inspector drawer for deep node traceability.
- `lib/graph.ts`: Layout calculation algorithms, search filtering, and node collapse helpers.

## 7. Relevant Backend Routes and Endpoints
- `GET /api/v1/research/graph`: Generates and returns graph nodes and edges for the active workspace scope.
- `GET /api/v1/research/graph/node/{entity_type}/{entity_id}`: Fetches detailed traceability metadata for a specific node.

## 8. Relevant Services and Agents
- `app.research.graph_service`: Entity-relationship graph generator.
- `app.collaboration.permission_service`: Enforces workspace boundary filtering on all graph entities.

## 9. Database Tables and Relationships
Projects data across virtually all core tables:
- `investigations`, `claims`, `evidence`, `sources`, `documents`
- `autonomous_research_workflows`, `research_workflow_cycles`, `research_actions`
- `debate_rounds`, `agent_arguments`, `adjudication_decisions`
- `research_gaps`, `research_hypotheses`, `research_contradictions`, `research_trend_topics`

## 10. Inputs and Outputs
- **Query Parameters**: `investigation_id` (UUID, optional), `include_sources` (bool), `max_nodes` (int).
- **Output (`KnowledgeGraphResponse`)**:
  ```json
  {
    "nodes": [
      {
        "id": "claim-1",
        "type": "claim",
        "label": "GLP-1 RA therapy produces significant body weight reduction.",
        "entity_id": "UUID",
        "metadata": { "confidence": 0.88, "status": "verified" }
      }
    ],
    "edges": [
      {
        "id": "e-1",
        "source": "evidence-1",
        "target": "claim-1",
        "relationship_type": "supports"
      }
    ]
  }
  ```

## 11. AI Provider Dependencies
None. Graph generation is 100% deterministic, querying persisted relational entities and explicit foreign keys.

## 12. External API Dependencies
None.

## 13. Configuration Requirements
- `NEOMON_DATABASE_URL`: Relational database connection.

## 14. Error Handling and Limitations
- **Zero Evidence**: Renders an accessible empty state with instructions to run an investigation first.
- **Large Graphs (>500 nodes)**: The backend applies pagination/capping heuristics (`max_nodes=500`) to prevent client-side WebGL/Canvas frame drops.

## 15. Security and Permission Considerations
- Nodes are strictly filtered by workspace tenancy. A user never sees nodes originating from investigations in workspaces they cannot access.

## 16. Related Features and Dependencies
- **Evidence Explorer** (`docs/features/evidence-workspace.md`): Evidence detail panel links directly to the Evidence Explorer.
- **Contradiction Intelligence** (`docs/features/contradiction-intelligence.md`): Contradiction nodes reflect active resolution statuses.

## 17. Relevant Tests and How to Run Them
- **Frontend Tests**:
  - `node --test tests/workspace-ui.test.mjs` (Asserts graph helpers, filtering, layout determinism, and detail drawer rendering).
- **Backend Tests**:
  - `python -m pytest backend/tests/test_research_engine.py -q`
