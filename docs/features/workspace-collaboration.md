# Feature Specification: Multi-User Collaborative Workspaces & Governance

## 1. Feature Overview
NEOMON implements enterprise-grade **Multi-User Collaborative Workspaces** (`/workspaces`). The system enforces strict multi-tenant data isolation, role-based access control (RBAC: **Admin**, **Researcher**, **Reviewer**, **Viewer**), member invitations, peer review requests, in-context evidence annotations, threaded discussions, and an immutable scientific audit activity stream.

## 2. Purpose and Problem Solved
Modern academic and enterprise scientific research is fundamentally collaborative: investigators, peer reviewers, and ethics boards must co-examine evidentiary materials. Public chat interfaces lack multi-user collaboration and tenancy controls. NEOMON solves this by:
- Partitioning all investigations, claims, evidence, and reports into isolated workspaces.
- Supporting strict role hierarchies preventing unauthorized modifications.
- Enabling in-context scientific peer reviews with formal approval/rejection decisions.
- Recording an immutable audit activity stream of every data mutation for compliance.

## 3. Where Users Access It
- **Dedicated Route**: `/workspaces` (Workspace Hub) and `/workspaces/[id]` (Workspace Detail).
- **Workspace Switcher**: Top header dropdown on all pages (`components/app-shell.tsx`).
- **In-Investigation**: Collaboration drawer (Reviews, Comments, Annotations) on `/investigations/[id]`.

## 4. Step-by-Step User Workflow
1. Navigate to `/workspaces`.
2. Inspect the **Workspace Management Cards**:
   - Lists workspaces where the user holds membership.
   - Displays investigator count, investigation count, user role (`owner`, `admin`, `researcher`, `reviewer`, `viewer`), and active tag.
3. Switch Active Workspace:
   - Click the workspace switcher dropdown in the header to change the global session scope.
4. Manage Members (`/workspaces/[id]/members`):
   - Click **"+ Invite Member"**.
   - Input colleague's email address and assign a role:
     - `Admin`: Full workspace management, member governance, settings.
     - `Researcher`: Create investigations, run multi-agent debates, edit evidence.
     - `Reviewer`: Review investigations, submit peer review decisions, add annotations.
     - `Viewer`: Read-only access to investigations, reports, and knowledge graphs.
5. In-Context Peer Review (`/reviews`):
   - From `/investigations/[id]`, click **"Request Peer Review"**.
   - Assign to a workspace reviewer.
   - The reviewer opens `/reviews`, inspects evidence, leaves threaded feedback, and records a formal decision (`Approved`, `Changes Requested`, `Rejected`).
6. Scientific Audit Log (`/workspaces/[id]/activity`):
   - Inspect chronological activity stream filtered by category (`Investigations`, `Reviews`, `Annotations`, `Discussions`, `Membership`).

## 5. How the Feature Works Internally
1. When a user registers, the system automatically provisions their personal default workspace and adds them as `owner` in `workspace_members`.
2. Every request passes through the `PermissionService` (`app.collaboration.permission_service`):
   - Inspects `Authorization: Bearer <token>` to identify the user.
   - Extracts `workspace_id` from the payload or session context.
   - Verifies the user holds an active membership record with the required minimum role.
3. In-context collaboration tools:
   - **Comment Threads**: Stored in `comment_threads` and `comments` with foreign key links to `investigations`, `claims`, or `evidence`.
   - **Evidence Annotations**: Stored in `evidence_annotations` with author ID and text.
   - **Peer Reviews**: Managed via `review_requests` and `review_decisions`.
4. Activity Logger: Key mutations trigger an asynchronous task recording an event in `workspace_activities`.

## 6. Relevant Frontend Pages and Components
- `app/workspaces/page.tsx`: Workspace list and creation hub.
- `app/workspaces/[id]/page.tsx`: Workspace overview dashboard.
- `app/workspaces/[id]/members/page.tsx`: Member roster and invitation controls.
- `app/workspaces/[id]/activity/page.tsx`: Chronological scientific audit log.
- `app/reviews/page.tsx`: Dedicated peer review inbox.
- `components/collaboration-panel.tsx`: In-context discussion and review drawer.
- `lib/collaboration.ts`: Client API methods for workspaces, members, reviews, and comments.

## 7. Relevant Backend Routes and Endpoints
- `GET /api/v1/workspaces`: Lists accessible workspaces for the current user.
- `POST /api/v1/workspaces`: Creates a new multi-user workspace.
- `GET /api/v1/workspaces/{id}/members`: Lists workspace members and assigned roles.
- `POST /api/v1/workspaces/{id}/invitations`: Sends a member invitation.
- `POST /api/v1/collaboration/reviews`: Creates a formal peer review request.
- `POST /api/v1/collaboration/reviews/{id}/decisions`: Submits a peer review ruling.
- `GET /api/v1/workspaces/{id}/activities`: Fetches paginated workspace audit stream.

## 8. Relevant Services and Agents
- `app.collaboration.permission_service.PermissionService`: Centralized RBAC and tenant authorization guard.
- `app.collaboration.workspace_service`: Member lifecycle, invitations, and activity logging.

## 9. Database Tables and Relationships
- `workspaces`: Container entity (`id`, `name`, `description`, `owner_id`, `created_at`).
- `workspace_members`: User membership mapping (`workspace_id`, `user_id`, `role`).
- `workspace_invitations`: Pending invitations (`id`, `workspace_id`, `inviter_id`, `email`, `role`, `status`).
- `review_requests`: Peer review requests (`id`, `investigation_id`, `requester_id`, `reviewer_id`, `status`).
- `review_decisions`: Formal review rulings (`id`, `request_id`, `decision`, `comments`).
- `evidence_annotations`: Highlights and margin notes on evidence.
- `comment_threads`: Discussion roots attached to entities.
- `comments`: Threaded replies within discussion threads.
- `workspace_activities`: Audit log entries (`id`, `workspace_id`, `actor_id`, `action_type`, `entity_type`, `created_at`).

## 10. Inputs and Outputs
- **Invitation Request**:
  ```json
  {
    "email": "colleague@university.edu",
    "role": "reviewer"
  }
  ```
- **Review Decision Request**:
  ```json
  {
    "decision": "approved",
    "comments": "Methodology audit confirms robust sample size. Approved for synthesis."
  }
  ```

## 11. AI Provider Dependencies
None. Collaboration tools are deterministic administrative and relational primitives.

## 12. External API Dependencies
None.

## 13. Configuration Requirements
- `NEOMON_DATABASE_URL`: Relational database connection.

## 14. Error Handling and Limitations
- **Cross-Tenant Access Attempt**: Returns HTTP 403 Forbidden with message: *"You do not have access to this workspace."*
- **Role Violation**: Attempting an action above user privileges (e.g., Viewer attempting to launch research) returns HTTP 403: *"Operation requires minimum role: researcher."*

## 15. Security and Permission Considerations
- Workspace isolation is enforced at the database query layer: all select queries filter by `workspace_id`.
- Foreign key constraints prevent cross-workspace entity references.

## 16. Related Features and Dependencies
- **Investigations** (`docs/features/investigations.md`): Belong strictly to a parent workspace.
- **Notifications** (`docs/features/notifications.md`): Alerts users when invitations, comments, or review requests arrive.

## 17. Relevant Tests and How to Run Them
- **Backend Tests**:
  - `python -m pytest backend/tests/test_workspace_api.py -q`
  - `python -m pytest backend/tests/test_database_postgres.py -q`
- **Frontend Tests**:
  - `node --test tests/collaboration-ui.test.mjs`
