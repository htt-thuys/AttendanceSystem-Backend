# Frontend Guide

The detailed contract is in [API_DOC.md](./API_DOC.md). This file focuses on build order, UX guidance, and frontend conventions.

## Build Order

1. Login, auth context, token storage, and role-based route guards.
2. Recognition Mode for tablet/camera usage.
3. Unknown Queue.
4. Recognition Logs.
5. Employee List.
6. Employee Detail with `Info`, `Vectors`, `History`, and `Account` tabs.
7. Settings and Cleanup.
8. Dashboard, Attendance, and Export.
9. Self-service.

## Recognition Mode

- Prefer a dedicated page with few controls, suitable for a tablet placed at an entrance.
- For event mode, show active/upcoming events from `GET /api/events/upcoming-public` as a selectable list. If no event is selected, send no `event_id`.
- `GET /api/events/upcoming-public` only returns events that are currently running or start within the admin-configured `event_tablet_lookahead_minutes` window.
- If the user selects an upcoming event before `starts_at`, still send its `event_id`; backend will attach recognition and unknown queue rows to that event until `ends_at`.
- For admin event dropdown filters, avoid loading inactive history. Use `GET /api/events?status=running&limit=...`, `GET /api/events?status=upcoming&limit=...`, or the tablet public upcoming endpoint depending on the screen. Use `status=inactive` only on event management screens that intentionally inspect deactivated events.
- When an event is selected, send `event_id` with `/api/recognition` and show both normal recognition data and active event data from the response.
- For `sure` results, keep the popup editable until timeout. On timeout call `/api/recognition/confirm` with `sure_ok`; if the user corrects the employee, call `sure_wrong_choose` or `sure_wrong_no_match`.
- For tablet employee correction, use `GET /api/employees/active-public`; do not show inactive employees on tablet.
- For tablet recent logs, call `GET /api/recognition-logs/recent-public?event_id=<id>` when an event is selected, or `GET /api/recognition-logs/recent-public?default_event_only=true` for normal/default mode.
- Show a large camera preview, clear loading state, and readable result popup.
- Add a cooldown after each recognition to avoid sending continuous requests.
- Support full-screen mode.
- If the API returns an AI-service `502`, show it as a temporary system error, not as `no_face`.

## Unknown Queue

- Use a card list with a large image, `attempt_count`, first-seen time, and last-seen time.
- Provide fast actions: assign to an existing employee, create a new employee, or reject.
- Use a modal for employee selection and only show active employees. Assigning unknown queue to inactive/deleted employees is rejected by the backend.
- Use `event_id` filtering when processing unknown faces from one event. Use `event_scope=default` for normal/default unknown faces with no selected event, and `event_scope=inactive` for unresolved unknown faces from inactive events. Queue items include `event_title` for display.
- Add sorting by `last_seen_at` or `attempt_count`.

## Employee UX

- Deleted employees do not appear in normal lists. The frontend does not need to treat `deleted` as a regular daily admin status.
- Admin/reviewer employee management should use `GET /api/employees`, which returns active and inactive employees unless a `status` filter is supplied.
- Recommended badges: `active`, `inactive`.
- `anonymize` permanently destroys personal/biometric data and needs a clear confirmation dialog.
- `deactivate` can be restored; `anonymize` cannot be restored.
- Vector deletion is permanent and should have a separate confirmation dialog.
- Employee detail should warn when an employee is active but has no vector.

## Recognition Logs

- Recommended filter presets: today, last 7 days, unconfirmed.
- Admin/reviewer logs hide pending popup logs by default. Add `include_pending=true` only for a debug/unfinished-confirm view.
- Tables should show image previews when `face_image_url` exists.
- Some logs may no longer have images or employee names because of cleanup/anonymize. The UI should show a fallback instead of crashing.

## Settings

- Thresholds are sensitive numeric values; validate ranges on the frontend before sending requests.
- Warn when a threshold is far lower or higher than its default.
- `event_tablet_lookahead_minutes` controls how early upcoming events appear on the tablet event selector.
- `Reset default` and `Cleanup now` should have confirmation dialogs.

## Self-Service

- Crop avatars before upload when possible to improve vector quality.
- Password change should validate length and confirmation on the frontend.
- If an account is locked or an employee is anonymized, the backend blocks login; the frontend only needs normal auth-error handling.

## Role-Based UI

- `admin`: show all admin screens.
- `reviewer`: show Unknown Queue, Recognition Logs, Meetings (read-only), Employee History when needed, and self-service.
- `employee`: show self-service only.

## Image Rendering

- Prefer API `*_url` fields.
- If a URL is null, show a placeholder.
- Do not compose URLs from paths unless the API does not provide a URL field.
