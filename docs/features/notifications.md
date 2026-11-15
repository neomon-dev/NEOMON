# Feature Specification: Notification Delivery Center & Preferences

## 1. Feature Overview
The **Notification Delivery Center** (`/notifications`) provides an asynchronous alert and notification system for multi-user collaboration. It notifies researchers of critical workflow events: peer review requests, review decisions, workspace member invitations, evidence annotations, and discussion replies. The platform supports unread badge counters, batch read marking, and granular user preferences for in-app alerts and email notifications.

## 2. Purpose and Problem Solved
In collaborative research environments, investigators need timely alerts when their work is reviewed, when an adversarial debate finishes, or when a colleague challenges an evidence quote. The Notification Center solves this by:
- Consolidating collaborative alerts into an inbox with unread counts.
- Providing deep links directly to the referenced investigation or discussion thread.
- Allowing users to toggle notification delivery channels (in-app vs. email digests).
- Preventing alert fatigue through category filtering.

## 3. Where Users Access It
- **Dedicated Route**: `/notifications` (Notification Inbox).
- **Header Icon**: Bell icon with real-time unread badge counter in the top bar (`components/app-shell.tsx`).
- **Settings**: Notification delivery toggles on `/settings`.

## 4. Step-by-Step User Workflow
1. Navigate to `/notifications` (or click the bell icon in the top header).
2. Inspect the **Notification Feed**:
   - Lists notifications categorized by type: `review_requested`, `review_completed`, `invitation_received`, `annotation_added`, `comment_reply`.
   - Displays sender name, timestamp, and short preview text.
3. Filter Notifications:
   - Toggle **"All Notifications"** vs. **"Unread Only"**.
4. Take Action:
   - Click a notification card to jump directly to the target investigation, review inbox, or discussion thread.
   - Click **"Mark as Read"** on individual notifications, or click **"Mark All as Read"** to clear the unread counter.
5. Configure Delivery Preferences:
   - In `/settings`, toggle **In-App Notifications** and **Email Digest Notifications**.

## 5. How the Feature Works Internally
1. When collaborative actions occur (e.g. `POST /reviews` or adding an annotation), the service calls `app.collaboration.notification_service.create_notification`.
2. The notification service:
   - Checks the target recipient's `notification_preferences`.
   - Persists a `notifications` record with `user_id`, `workspace_id`, `notification_type`, `title`, `message`, `target_entity_type`, `target_entity_id`, and `is_read=False`.
3. The client `lib/auth-context.tsx` polls `/api/v1/collaboration/notifications/unread-count` periodically and updates the bell icon badge.
4. Marking notifications as read executes `POST /api/v1/collaboration/notifications/{id}/read` or `POST /api/v1/collaboration/notifications/read-all`.

## 6. Relevant Frontend Pages and Components
- `app/notifications/page.tsx`: Notification list page with filter tabs.
- `components/app-shell.tsx`: Bell icon with unread indicator badge.
- `lib/collaboration.ts`: API methods for fetching and updating notifications.

## 7. Relevant Backend Routes and Endpoints
- `GET /api/v1/collaboration/notifications`: Returns paginated notifications for the authenticated user.
- `GET /api/v1/collaboration/notifications/unread-count`: Returns integer count of unread notifications.
- `POST /api/v1/collaboration/notifications/{id}/read`: Marks a single notification as read.
- `POST /api/v1/collaboration/notifications/read-all`: Marks all notifications as read for the current user.
- `GET /api/v1/collaboration/notification-preferences`: Retrieves user delivery preferences.
- `PUT /api/v1/collaboration/notification-preferences`: Updates delivery preferences.

## 8. Relevant Services and Agents
- `app.collaboration.notification_service.NotificationService`: Creation, dispatch, and preference engine.

## 9. Database Tables and Relationships
- `notifications`: Stores `id`, `user_id`, `workspace_id`, `notification_type`, `title`, `message`, `target_entity_type`, `target_entity_id`, `is_read`, `created_at`.
- `notification_preferences`: Stores user-level delivery toggles (`user_id`, `in_app_notifications_enabled`, `email_notifications_enabled`).
- `users`: Recipient user entity linked via `user_id`.

## 10. Inputs and Outputs
- **Unread Count Response**:
  ```json
  {
    "unread_count": 3
  }
  ```
- **Notifications List Response**:
  Array of `NotificationResponse` objects containing UUID, notification type, title, message, target links, read status, and ISO timestamp.

## 11. AI Provider Dependencies
None.

## 12. External API Dependencies
None. (SMTP email dispatch is simulated/mocked in local environments).

## 13. Configuration Requirements
- `NEOMON_DATABASE_URL`: Relational database connection.

## 14. Error Handling and Limitations
- **Notification Deletion**: System automatically purges notifications older than 90 days to maintain database performance.
- **Empty State**: When no notifications exist, renders a clean, accessible inbox illustration.

## 15. Security and Permission Considerations
- Users can only query, read, or modify their own notifications.
- The `user_id` is extracted strictly from the verified session token, preventing horizontal privilege escalation.

## 16. Related Features and Dependencies
- **Workspaces** (`docs/features/workspace-collaboration.md`): Review requests and invitations generate notifications.
- **Authentication** (`docs/features/authentication-and-roles.md`): Scoped strictly to the authenticated user.

## 17. Relevant Tests and How to Run Them
- **Backend Tests**:
  - `python -m pytest backend/tests/test_workspace_api.py -q`
- **Frontend Tests**:
  - `node --test tests/collaboration-ui.test.mjs`
