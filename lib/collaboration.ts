import { requestJson } from "@/lib/api";

export interface User {
  id: string;
  email: string;
  display_name: string;
  bio?: string | null;
  role: string;
  status: string;
  created_at?: string | null;
}

export interface AuthTokenResponse {
  user: User;
  session_token: string;
  token_type: string;
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  owner_id: string;
  status: string;
  settings: {
    require_independent_review?: boolean;
    max_autonomous_budget?: number;
    allow_member_invitations?: boolean;
    [key: string]: unknown;
  };
  created_at?: string | null;
  updated_at?: string | null;
  user_role?: string | null;
  member_count: number;
  investigation_count: number;
}

export interface WorkspaceMember {
  id: string;
  workspace_id: string;
  user_id: string;
  email: string;
  display_name: string;
  role: string;
  status: string;
  joined_at?: string | null;
}

export interface WorkspaceInvitation {
  id: string;
  workspace_id: string;
  email: string;
  role: string;
  status: string;
  inviter_name?: string | null;
  expires_at?: string | null;
  created_at?: string | null;
  invite_token?: string | null;
  invite_link?: string | null;
}

export interface Comment {
  id: string;
  thread_id: string;
  author_id: string;
  author_name: string;
  parent_comment_id?: string | null;
  content: string;
  is_edited: boolean;
  is_deleted: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CommentThread {
  id: string;
  workspace_id: string;
  investigation_id?: string | null;
  target_entity_type: string;
  target_entity_id: string;
  title?: string | null;
  status: string;
  created_by_id: string;
  creator_name: string;
  comment_count: number;
  comments: Comment[];
  created_at?: string | null;
  resolved_at?: string | null;
}

export interface EvidenceAnnotation {
  id: string;
  workspace_id: string;
  investigation_id: string;
  evidence_id: string;
  author_id: string;
  author_name: string;
  annotation_type: string;
  comment: string;
  reviewer_rationale?: string | null;
  status: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ReviewDecision {
  id: string;
  reviewer_id: string;
  reviewer_name: string;
  decision: string;
  rationale: string;
  created_at?: string | null;
}

export interface ReviewRequest {
  id: string;
  workspace_id: string;
  investigation_id: string;
  target_type: string;
  target_id: string;
  target_version?: string | null;
  requester_id: string;
  requester_name: string;
  title: string;
  description?: string | null;
  status: string;
  requires_independent_review: boolean;
  decisions: ReviewDecision[];
  created_at?: string | null;
  updated_at?: string | null;
}

export interface NotificationItem {
  id: string;
  workspace_id?: string | null;
  actor_id?: string | null;
  actor_name: string;
  event_type: string;
  title: string;
  message: string;
  link_url?: string | null;
  is_read: boolean;
  created_at?: string | null;
}

export interface WorkspaceActivity {
  id: string;
  workspace_id: string;
  actor_id?: string | null;
  actor_name: string;
  actor_email?: string | null;
  action_type: string;
  entity_type: string;
  entity_id?: string | null;
  summary: string;
  metadata: Record<string, unknown>;
  created_at?: string | null;
}

// ==========================================
// AUTH API
// ==========================================

export async function loginUser(email: string, password: string): Promise<AuthTokenResponse> {
  const res = await requestJson<AuthTokenResponse>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (typeof window !== "undefined" && res.session_token) {
    localStorage.setItem("neomon_session_token", res.session_token);
  }
  return res;
}

export async function registerUser(email: string, password: string, displayName: string, bio?: string): Promise<AuthTokenResponse> {
  const res = await requestJson<AuthTokenResponse>("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, display_name: displayName, bio }),
  });
  if (typeof window !== "undefined" && res.session_token) {
    localStorage.setItem("neomon_session_token", res.session_token);
  }
  return res;
}

export async function logoutUser(): Promise<void> {
  try {
    await requestJson("/auth/logout", { method: "POST" });
  } finally {
    if (typeof window !== "undefined") {
      localStorage.removeItem("neomon_session_token");
    }
  }
}

export async function getCurrentUser(): Promise<User | null> {
  try {
    return await requestJson<User>("/auth/me");
  } catch {
    return null;
  }
}

export async function updateProfile(displayName?: string, bio?: string): Promise<User> {
  return requestJson<User>("/auth/profile", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ display_name: displayName, bio }),
  });
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  await requestJson("/auth/password/change", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  });
}

export async function requestPasswordReset(email: string): Promise<{ reset_token?: string; reset_link?: string }> {
  return requestJson<{ reset_token?: string; reset_link?: string }>("/auth/password/reset-request", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
}

export async function confirmPasswordReset(token: string, newPassword: string): Promise<void> {
  await requestJson("/auth/password/reset-confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password: newPassword }),
  });
}

// ==========================================
// WORKSPACE API
// ==========================================

export async function listWorkspaces(): Promise<Workspace[]> {
  return requestJson<Workspace[]>("/workspaces");
}

export async function getWorkspace(id: string): Promise<Workspace> {
  return requestJson<Workspace>(`/workspaces/${id}`);
}

export async function createWorkspace(name: string, description?: string, settings?: Record<string, unknown>): Promise<Workspace> {
  return requestJson<Workspace>("/workspaces", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description, settings }),
  });
}

export async function updateWorkspace(id: string, name?: string, description?: string, settings?: Record<string, unknown>): Promise<Workspace> {
  return requestJson<Workspace>(`/workspaces/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description, settings }),
  });
}

export async function archiveWorkspace(id: string): Promise<void> {
  await requestJson(`/workspaces/${id}/archive`, { method: "POST" });
}

export async function restoreWorkspace(id: string): Promise<void> {
  await requestJson(`/workspaces/${id}/restore`, { method: "POST" });
}

export async function listWorkspaceMembers(id: string): Promise<WorkspaceMember[]> {
  return requestJson<WorkspaceMember[]>(`/workspaces/${id}/members`);
}

export async function updateMemberRole(workspaceId: string, userId: string, role: string): Promise<void> {
  await requestJson(`/workspaces/${workspaceId}/members/${userId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role }),
  });
}

export async function removeMember(workspaceId: string, userId: string): Promise<void> {
  await requestJson(`/workspaces/${workspaceId}/members/${userId}`, { method: "DELETE" });
}

export async function transferOwnership(workspaceId: string, newOwnerId: string): Promise<void> {
  await requestJson(`/workspaces/${workspaceId}/transfer-ownership`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ new_owner_id: newOwnerId }),
  });
}

export async function getWorkspaceActivity(workspaceId: string, limit = 50): Promise<WorkspaceActivity[]> {
  return requestJson<WorkspaceActivity[]>(`/workspaces/${workspaceId}/activity?limit=${limit}`);
}

// ==========================================
// INVITATION API
// ==========================================

export async function inviteMember(workspaceId: string, email: string, role = "researcher"): Promise<WorkspaceInvitation> {
  return requestJson<WorkspaceInvitation>(`/workspaces/${workspaceId}/invitations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, role }),
  });
}

export async function listWorkspaceInvitations(workspaceId: string): Promise<WorkspaceInvitation[]> {
  return requestJson<WorkspaceInvitation[]>(`/workspaces/${workspaceId}/invitations`);
}

export async function lookupInvitation(token: string): Promise<{
  id: string;
  workspace_id: string;
  workspace_name: string;
  email: string;
  role: string;
  status: string;
  expires_at?: string | null;
}> {
  return requestJson(`/invitations/lookup?token=${encodeURIComponent(token)}`);
}

export async function acceptInvitation(token: string): Promise<{ success: boolean; workspace_id: string; workspace_name: string; role: string }> {
  return requestJson("/invitations/accept", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
}

export async function declineInvitation(token: string): Promise<void> {
  await requestJson("/invitations/decline", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
}

export async function revokeInvitation(workspaceId: string, invitationId: string): Promise<void> {
  await requestJson(`/workspaces/${workspaceId}/invitations/${invitationId}`, { method: "DELETE" });
}

// ==========================================
// THREADS & COMMENTS API
// ==========================================

export async function listThreads(params: {
  workspace_id: string;
  investigation_id?: string;
  target_entity_type?: string;
  target_entity_id?: string;
  status?: string;
}): Promise<CommentThread[]> {
  const query = new URLSearchParams({ workspace_id: params.workspace_id });
  if (params.investigation_id) query.set("investigation_id", params.investigation_id);
  if (params.target_entity_type) query.set("target_entity_type", params.target_entity_type);
  if (params.target_entity_id) query.set("target_entity_id", params.target_entity_id);
  if (params.status) query.set("status", params.status);
  return requestJson<CommentThread[]>(`/collaboration/threads?${query.toString()}`);
}

export async function getThread(threadId: string): Promise<CommentThread> {
  return requestJson<CommentThread>(`/collaboration/threads/${threadId}`);
}

export async function createThread(payload: {
  workspace_id: string;
  target_entity_type: string;
  target_entity_id: string;
  content: string;
  title?: string;
  investigation_id?: string;
}): Promise<CommentThread> {
  return requestJson<CommentThread>(`/collaboration/threads?workspace_id=${payload.workspace_id}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target_entity_type: payload.target_entity_type,
      target_entity_id: payload.target_entity_id,
      content: payload.content,
      title: payload.title,
      investigation_id: payload.investigation_id,
    }),
  });
}

export async function addComment(threadId: string, content: string, parentCommentId?: string): Promise<Comment> {
  return requestJson<Comment>(`/collaboration/threads/${threadId}/comments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, parent_comment_id: parentCommentId }),
  });
}

export async function resolveThread(threadId: string): Promise<void> {
  await requestJson(`/collaboration/threads/${threadId}/resolve`, { method: "POST" });
}

export async function reopenThread(threadId: string): Promise<void> {
  await requestJson(`/collaboration/threads/${threadId}/reopen`, { method: "POST" });
}

export async function editComment(commentId: string, content: string): Promise<void> {
  await requestJson(`/collaboration/comments/${commentId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
}

export async function deleteComment(commentId: string): Promise<void> {
  await requestJson(`/collaboration/comments/${commentId}`, { method: "DELETE" });
}

// ==========================================
// EVIDENCE ANNOTATIONS API
// ==========================================

export async function listAnnotations(params: {
  workspace_id: string;
  investigation_id?: string;
  evidence_id?: string;
  status?: string;
}): Promise<EvidenceAnnotation[]> {
  const query = new URLSearchParams({ workspace_id: params.workspace_id });
  if (params.investigation_id) query.set("investigation_id", params.investigation_id);
  if (params.evidence_id) query.set("evidence_id", params.evidence_id);
  if (params.status) query.set("status", params.status);
  return requestJson<EvidenceAnnotation[]>(`/collaboration/annotations?${query.toString()}`);
}

export async function createAnnotation(payload: {
  workspace_id: string;
  investigation_id: string;
  evidence_id: string;
  annotation_type: string;
  comment: string;
  reviewer_rationale?: string;
}): Promise<EvidenceAnnotation> {
  return requestJson<EvidenceAnnotation>(`/collaboration/annotations?workspace_id=${payload.workspace_id}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      investigation_id: payload.investigation_id,
      evidence_id: payload.evidence_id,
      annotation_type: payload.annotation_type,
      comment: payload.comment,
      reviewer_rationale: payload.reviewer_rationale,
    }),
  });
}

export async function updateAnnotationStatus(annotationId: string, status: string, reviewerRationale?: string): Promise<void> {
  await requestJson(`/collaboration/annotations/${annotationId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, reviewer_rationale: reviewerRationale }),
  });
}

export async function deleteAnnotation(annotationId: string): Promise<void> {
  await requestJson(`/collaboration/annotations/${annotationId}`, { method: "DELETE" });
}

// ==========================================
// REVIEWS API
// ==========================================

export async function listReviewRequests(params: {
  workspace_id: string;
  investigation_id?: string;
  status?: string;
}): Promise<ReviewRequest[]> {
  const query = new URLSearchParams({ workspace_id: params.workspace_id });
  if (params.investigation_id) query.set("investigation_id", params.investigation_id);
  if (params.status) query.set("status", params.status);
  return requestJson<ReviewRequest[]>(`/collaboration/reviews?${query.toString()}`);
}

export async function getReviewRequest(requestId: string): Promise<ReviewRequest> {
  return requestJson<ReviewRequest>(`/collaboration/reviews/${requestId}`);
}

export async function createReviewRequest(payload: {
  workspace_id: string;
  investigation_id: string;
  target_type: string;
  target_id: string;
  title: string;
  description?: string;
  target_version?: string;
  requires_independent_review?: boolean;
}): Promise<ReviewRequest> {
  return requestJson<ReviewRequest>(`/collaboration/reviews?workspace_id=${payload.workspace_id}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function submitReviewDecision(requestId: string, decision: string, rationale: string): Promise<ReviewRequest> {
  return requestJson<ReviewRequest>(`/collaboration/reviews/${requestId}/decisions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision, rationale }),
  });
}

export async function withdrawReviewRequest(requestId: string): Promise<void> {
  await requestJson(`/collaboration/reviews/${requestId}/withdraw`, { method: "POST" });
}

// ==========================================
// NOTIFICATIONS API
// ==========================================

export async function listNotifications(limit = 50, unreadOnly = false): Promise<NotificationItem[]> {
  return requestJson<NotificationItem[]>(`/collaboration/notifications?limit=${limit}&unread_only=${unreadOnly}`);
}

export async function getUnreadNotificationCount(): Promise<number> {
  const res = await requestJson<{ unread_count: number }>("/collaboration/notifications/unread-count");
  return res.unread_count;
}

export async function markNotificationRead(notificationId: string): Promise<void> {
  await requestJson(`/collaboration/notifications/${notificationId}/read`, { method: "PATCH" });
}

export async function markAllNotificationsRead(): Promise<void> {
  await requestJson("/collaboration/notifications/mark-all-read", { method: "POST" });
}

export async function getNotificationPreferences(): Promise<{ email_notifications_enabled: boolean; in_app_notifications_enabled: boolean }> {
  return requestJson("/collaboration/notifications/preferences");
}

export async function updateNotificationPreferences(emailEnabled: boolean, inAppEnabled: boolean): Promise<void> {
  await requestJson("/collaboration/notifications/preferences", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email_notifications_enabled: emailEnabled, in_app_notifications_enabled: inAppEnabled }),
  });
}
