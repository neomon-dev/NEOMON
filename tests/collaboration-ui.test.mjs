import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import test from "node:test";
import ts from "typescript";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

const require = createRequire(import.meta.url);
const rootDir = process.cwd();

function loadTsModule(relPath, mocks = {}) {
  const fullPath = path.join(rootDir, relPath);
  const source = fs.readFileSync(fullPath, "utf8");
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      jsx: ts.JsxEmit.ReactJSX,
      esModuleInterop: true,
    },
    fileName: fullPath,
  }).outputText;

  const mod = { exports: {} };
  const localRequire = (specifier) => {
    if (specifier in mocks) return mocks[specifier];
    if (specifier.startsWith("@/")) {
      const target = specifier.slice(2);
      if (target in mocks) return mocks[target];
      const targetPath = fs.existsSync(path.join(rootDir, `${target}.tsx`))
        ? `${target}.tsx`
        : fs.existsSync(path.join(rootDir, `${target}.ts`))
        ? `${target}.ts`
        : `${target}.ts`;
      return loadTsModule(targetPath, mocks);
    }
    if (specifier === "react" || specifier.startsWith("react/")) {
      return require(specifier);
    }
    return require(specifier);
  };

  const fn = new Function("exports", "require", "module", "__filename", "__dirname", compiled);
  fn(mod.exports, localRequire, mod, fullPath, path.dirname(fullPath));
  return mod.exports;
}

const mockLink = ({ href, children, ...rest }) => React.createElement("a", { href, ...rest }, children);

test("Collaboration API module defines full suite of multi-user workspace methods", () => {
  const collab = loadTsModule("lib/collaboration.ts", {
    "@/lib/api": {
      requestJson: async () => ({}),
    },
  });

  // Auth methods
  assert.equal(typeof collab.loginUser, "function");
  assert.equal(typeof collab.registerUser, "function");
  assert.equal(typeof collab.getCurrentUser, "function");
  assert.equal(typeof collab.logoutUser, "function");

  // Workspace methods
  assert.equal(typeof collab.listWorkspaces, "function");
  assert.equal(typeof collab.getWorkspace, "function");
  assert.equal(typeof collab.createWorkspace, "function");
  assert.equal(typeof collab.updateWorkspace, "function");
  assert.equal(typeof collab.archiveWorkspace, "function");
  assert.equal(typeof collab.restoreWorkspace, "function");
  assert.equal(typeof collab.listWorkspaceMembers, "function");
  assert.equal(typeof collab.transferOwnership, "function");
  assert.equal(typeof collab.getWorkspaceActivity, "function");

  // Invitation methods
  assert.equal(typeof collab.inviteMember, "function");
  assert.equal(typeof collab.lookupInvitation, "function");
  assert.equal(typeof collab.acceptInvitation, "function");
  assert.equal(typeof collab.declineInvitation, "function");

  // Discussions & Comments
  assert.equal(typeof collab.listThreads, "function");
  assert.equal(typeof collab.createThread, "function");
  assert.equal(typeof collab.addComment, "function");
  assert.equal(typeof collab.resolveThread, "function");

  // Annotations
  assert.equal(typeof collab.listAnnotations, "function");
  assert.equal(typeof collab.createAnnotation, "function");

  // Reviews & Decisions
  assert.equal(typeof collab.listReviewRequests, "function");
  assert.equal(typeof collab.createReviewRequest, "function");
  assert.equal(typeof collab.submitReviewDecision, "function");
  assert.equal(typeof collab.withdrawReviewRequest, "function");

  // Notifications
  assert.equal(typeof collab.listNotifications, "function");
  assert.equal(typeof collab.getUnreadNotificationCount, "function");
  assert.equal(typeof collab.markNotificationRead, "function");
  assert.equal(typeof collab.markAllNotificationsRead, "function");
});

test("CollaborationPanel renders Threaded Discussions, Annotations, and Peer Review triggers", () => {
  const mockUser = { id: "user-1", email: "lead@neomon.ai", display_name: "Lead Researcher", role: "lead" };
  const mockWorkspace = { id: "ws-1", name: "Quantum Physics Lab", slug: "quantum-lab", owner_id: "user-1", status: "active", settings: {}, member_count: 2, investigation_count: 1 };

  const { CollaborationPanel } = loadTsModule("components/collaboration-panel.tsx", {
    "next/link": { default: mockLink, __esModule: true },
    "@/lib/auth-context": {
      useAuth: () => ({
        user: mockUser,
        activeWorkspace: mockWorkspace,
        workspaces: [mockWorkspace],
      }),
    },
    "@/lib/collaboration": {
      listThreads: async () => [],
      listAnnotations: async () => [],
      listReviewRequests: async () => [],
      createThread: async () => ({}),
      addComment: async () => ({}),
      resolveThread: async () => ({}),
      reopenThread: async () => ({}),
      createAnnotation: async () => ({}),
      createReviewRequest: async () => ({}),
      submitReviewDecision: async () => ({}),
    },
  });

  const html = renderToStaticMarkup(React.createElement(CollaborationPanel, { investigationId: "inv-test-123" }));
  assert.match(html, /COLLABORATION &amp; GOVERNANCE/);
  assert.match(html, /Scientific Peer Review &amp; Collaborative Dialogue/);
  assert.match(html, /Discussions/);
  assert.match(html, /Evidence Annotations/);
  assert.match(html, /Peer Reviews/);
});

test("Milestone 10 route files exist for Workspaces, Auth, Reviews, Notifications, and Invitations", () => {
  const requiredRoutes = [
    "app/login/page.tsx",
    "app/register/page.tsx",
    "app/forgot-password/page.tsx",
    "app/profile/page.tsx",
    "app/workspaces/page.tsx",
    "app/workspaces/[id]/page.tsx",
    "app/workspaces/[id]/members/page.tsx",
    "app/workspaces/[id]/settings/page.tsx",
    "app/workspaces/[id]/activity/page.tsx",
    "app/invitations/page.tsx",
    "app/reviews/page.tsx",
    "app/notifications/page.tsx",
  ];

  for (const route of requiredRoutes) {
    const fullPath = path.join(rootDir, route);
    assert.equal(fs.existsSync(fullPath), true, `Route file must exist: ${route}`);
  }
});
