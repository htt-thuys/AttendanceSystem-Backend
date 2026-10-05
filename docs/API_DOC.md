# API Documentation - Face Recognition Attendance System

This document is the frontend integration contract for the current backend codebase. It is intentionally concise: use it to know which endpoint to call, which role is required, and which fields matter. For exact generated schema details, run the backend and open `http://127.0.0.1:8000/docs`.

## 1. General

- **API base URL:** `http://127.0.0.1:8000/api`
- **Health check:** `GET http://127.0.0.1:8000/health`
- **Public media:** `GET http://127.0.0.1:8000/media/<path>`
- **Auth header:** `Authorization: Bearer <access_token>`
- **Date format:** `YYYY-MM-DD`
- **Datetime format:** ISO 8601 string
- **CSV endpoints:** return `text/csv` with a `Content-Disposition` download filename.

## 2. Roles

| Role | Access summary |
| :--- | :------------- |
| Public | Health, login/refresh, recognition, recognition confirm, public recent logs, active employees, public events, public meetings. |
| employee | Own profile, password, notifications, attendance history, absence requests, meeting check-in/check-out/absence. |
| reviewer | Read/review operational views: employees list, recognition logs, unknown queue, event read views, meeting read views. |
| admin | Full management access: employees, users, cameras, attendance, meetings, events, settings, cleanup, dashboard, exports. |

## 3. Common Response Shapes

Common action response:

```json
{
  "success": true,
  "message": "optional message",
  "employee_id": 1
}
```

JWT token response:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

## 4. Auth

| Method | Path | Auth | Body | Response |
| :----- | :--- | :--- | :--- | :------- |
| POST | `/api/auth/login` | Public | `{ username, password }` | JWT token response |
| POST | `/api/auth/refresh` | Public | `{ refresh_token }` | JWT token response |

## 5. Recognition

| Method | Path | Auth | Request | Response |
| :----- | :--- | :--- | :------ | :------- |
| POST | `/api/recognition` | Public | `multipart/form-data`: `image` required, optional `camera_id`, `meeting_id`, `event_id` or `eventId` | `RecognizeResponse` |
| POST | `/api/recognition/confirm` | Public | `{ recognition_log_id, action, employee_id?, meeting_id?, event_id? }` | `{ success, message }` |

`RecognizeResponse` fields:

- `label`: `sure`, `review`, `unknown`, `no_face`, or spoof/AI error-related label.
- `recognition_log_id`: nullable log id used by confirm flow.
- `employee`: `{ id, full_name }` when a match is selected.
- `score`: top similarity score.
- `candidates`: list of `{ employee_id, score }` for review cases.
- `auto_attendance`: whether daily attendance was applied.
- `auto_meeting_checkin`: meeting participant/check-in id when meeting check-in was applied.
- `event_id`, `event`, `meeting_id`, `meeting`: selected context metadata.
- `log_saved`: false when cooldown prevents duplicate log writes.
- `live_score`, `spoof_score`: present when AI spoof/liveness data is returned.

Valid confirm `action` values currently handled by service logic:

- `sure_ok`
- `sure_wrong_choose`
- `sure_wrong_no_match`
- `review_correct`
- `review_choose`
- `review_no_match`

Important behavior:

- `POST /api/recognition` can apply daily attendance, meeting check-in, and event log linking depending on request context.
- Duplicate logs and repeated auto-actions are limited by `recognition_log_cooldown_minutes`.
- Meeting attendance is not yet updated after resolving an unknown-queue item. Treat this as a known backend gap.

## 6. Me / Self-Service

| Method | Path | Auth | Request / Query | Response |
| :----- | :--- | :--- | :-------------- | :------- |
| GET | `/api/me/profile` | employee/reviewer/admin | None | `MyProfileResponse` |
| PATCH | `/api/me/profile` | employee/reviewer/admin | `multipart/form-data`: optional `full_name`, `email`, `avatar` | `MyProfileResponse` |
| PATCH | `/api/me/password` | employee/reviewer/admin | `{ current_password, new_password }` | `{ success, message }` |
| GET | `/api/me/recognition-logs/today` | employee/reviewer/admin | `limit` default `100`, max `500` | list of current user's recognition logs |
| GET | `/api/me/attendance` | employee/reviewer/admin | `date_from?`, `date_to?`, `status?` | list of attendance rows |
| POST | `/api/me/attendance/absence-request` | employee/reviewer/admin | `{ date, reason }` | attendance row |
| POST | `/api/me/meetings/{meeting_id}/checkin` | employee/reviewer/admin | optional `{ note }` | `{ success, message }` |
| POST | `/api/me/meetings/{meeting_id}/checkout` | employee/reviewer/admin | optional `{ note }` | `{ success, message }` |
| POST | `/api/me/meetings/{meeting_id}/absence-request` | employee/reviewer/admin | optional `{ note }` | `{ success, message }` |

`MyProfileResponse` includes: `user_id`, `username`, `email`, `role`, `is_active`, `employee_id`, `full_name`, `employee_code`, `avatar_path`, `avatar_url`, `employee_status`, `created_at`.

## 7. Notifications

| Method | Path | Auth | Request / Query | Response |
| :----- | :--- | :--- | :-------------- | :------- |
| GET | `/api/me/notifications` | employee/reviewer/admin | `page` default `1`, `page_size` default `20`, `is_read?` | `{ items, total, page, page_size }` |
| GET | `/api/me/notifications/unread-count` | employee/reviewer/admin | None | `{ unread_count }` |
| PATCH | `/api/me/notifications/{notification_id}/read` | employee/reviewer/admin | None | `{ success, message }` |
| POST | `/api/me/notifications/read-all` | employee/reviewer/admin | `{ include_read=false }` | `{ success, message }` |

Notification item fields: `id`, `type`, `title`, `message`, `is_read`, `data`, `created_at`, `read_at`.

Known status: meeting invitation notifications are not complete yet. The notification APIs exist, but the invitation notification flow still needs backend completion.

## 8. Attendance

| Method | Path | Auth | Request / Query | Response |
| :----- | :--- | :--- | :-------------- | :------- |
| GET | `/api/attendance` | admin | `date_from?`, `date_to?`, `employee_id?`, `status?` | list of attendance rows |
| GET | `/api/attendance/today` | admin | None | `{ date, stats }` |
| GET | `/api/attendance/report` | admin | required `date_from`, `date_to`; optional `employee_id`, `status` | `{ date_from, date_to, stats, records }` |
| POST | `/api/attendance/export` | admin | `{ date_from?, date_to?, employee_id?, status?, format="csv" }` | CSV |
| PATCH | `/api/attendance/{record_id}` | admin | `{ status?, note? }` | attendance row |

Attendance row fields: `id`, `employee_id`, `employee_name`, `date`, `check_in_time`, `check_out_time`, `status`, `work_hours`, `note`, `meetings`, `events`.

Attendance stats fields: `total_employees`, `present_count`, `late_count`, `absent_count`, `excused_count`, `on_time_count`, `early_leave_count`, `half_day_count`.

## 9. Dashboard

| Method | Path | Auth | Query | Response |
| :----- | :--- | :--- | :---- | :------- |
| GET | `/api/dashboard/stats` | admin | None | `{ total_employees, attendance_today, recognition_today, unknown_faces }` |
| GET | `/api/dashboard/attendance-trend` | admin | required `date_from`, `date_to` | `{ date_from, date_to, items }` |
| GET | `/api/dashboard/recognition-activity` | admin | required `date_from`, `date_to` | `{ date_from, date_to, items }` |
| GET | `/api/dashboard/late-arrivals` | admin | `target_date?` defaults today | `{ date, items }` |
| GET | `/api/dashboard/camera-status` | admin | None | `{ items }` |

## 10. Employees

| Method | Path | Auth | Request / Query | Response |
| :----- | :--- | :--- | :-------------- | :------- |
| GET | `/api/employees/active-public` | Public | None | list of employee list items |
| GET | `/api/employees` | admin/reviewer | `status?` | list of employee list items |
| POST | `/api/employees` | admin | `multipart/form-data`: `full_name`, `employee_code`, `avatar`, optional `vector_images[]` | common action response |
| DELETE | `/api/employees/{emp_id}` | admin | None | common action response |
| POST | `/api/employees/{emp_id}/reactivate` | admin | None | common action response |
| POST | `/api/employees/{emp_id}/anonymize` | admin | None | common action response |
| PATCH | `/api/employees/{emp_id}/avatar` | admin | `multipart/form-data`: `avatar` | common action response |
| GET | `/api/employees/{emp_id}/vectors` | admin | None | list of vector items |
| POST | `/api/employees/{emp_id}/vectors` | admin | `multipart/form-data`: `vector_images[]` | common action response |
| DELETE | `/api/employees/{emp_id}/vectors/{vec_id}` | admin | None | common action response |
| GET | `/api/employees/{emp_id}/recognition-logs` | admin/reviewer | `date_from?`, `date_to?`, `limit` default `100`, max `500` | list of recognition log items |

Employee list item fields: `id`, `full_name`, `employee_code`, `avatar_path`, `avatar_url`, `status`, `vector_count`.

Vector item fields: `id`, `source`, `source_image_path`, `source_image_url`, `quality_score`, `score_at_create`, `created_at`.

## 11. Users / Accounts

| Method | Path | Auth | Request | Response |
| :----- | :--- | :--- | :------ | :------- |
| GET | `/api/employees/{emp_id}/account` | admin | None | employee account |
| POST | `/api/employees/{emp_id}/account` | admin | `{ username, email?, password, role="employee" }` | employee account |
| PATCH | `/api/users/{user_id}/password` | admin | `{ password }` | common action response |
| PATCH | `/api/users/{user_id}/status` | admin | `{ is_active }` | employee account |

Employee account fields: `user_id`, `username`, `email`, `role`, `is_active`, `employee_id`, `created_at`.

## 12. Cameras

| Method | Path | Auth | Request | Response |
| :----- | :--- | :--- | :------ | :------- |
| GET | `/api/cameras` | admin | None | list of cameras |
| POST | `/api/cameras` | admin | `{ location?, is_active=true }` | camera |
| PATCH | `/api/cameras/{camera_id}` | admin | `{ location? }` | camera |
| PATCH | `/api/cameras/{camera_id}/status` | admin | `{ is_active }` | camera |

Camera fields: `id`, `location`, `is_active`, plus `last_seen_at` in list/detail views.

## 13. Meetings

| Method | Path | Auth | Request / Query | Response |
| :----- | :--- | :--- | :-------------- | :------- |
| GET | `/api/meetings/list-public` | Public | None | list of active public meetings |
| GET | `/api/meetings` | admin/reviewer | `date_from?`, `date_to?`, `status?` | list of meetings |
| POST | `/api/meetings` | admin | `{ title, description?, scheduled_start, scheduled_end?, location?, camera_id?, employee_ids=[] }` | meeting detail |
| GET | `/api/meetings/{meeting_id}` | admin/reviewer | None | meeting detail |
| PATCH | `/api/meetings/{meeting_id}` | admin | any subset of meeting update fields | meeting detail |
| DELETE | `/api/meetings/{meeting_id}` | admin | None | `{ success, message }` |
| POST | `/api/meetings/{meeting_id}/complete` | admin | None | `{ success, message }` |
| POST | `/api/meetings/{meeting_id}/participants` | admin | `{ employee_ids }` | `{ success, message }` |
| DELETE | `/api/meetings/{meeting_id}/participants/{emp_id}` | admin | None | `{ success, message }` |
| GET | `/api/meetings/{meeting_id}/attendance` | admin/reviewer | None | meeting attendance summary |

Meeting detail fields: `id`, `title`, `description`, `scheduled_start`, `scheduled_end`, `actual_start`, `actual_end`, `location`, `camera_id`, `status`, `created_by`, `created_at`, `updated_at`, `participants`.

Participant fields: `id`, `employee_id`, `employee_name`, `status`, `check_in_time`, `check_in_log_id`, `check_out_time`, `check_out_log_id`, `note`.

Meeting attendance fields: `meeting_id`, `total_participants`, `present_count`, `late_count`, `absent_count`, `excused_count`, `invited_count`, `participants`.

## 14. Events

| Method | Path | Auth | Request / Query | Response |
| :----- | :--- | :--- | :-------------- | :------- |
| GET | `/api/events/list-public` | Public | `limit?` min `1`, max `100` | active public events |
| GET | `/api/events/upcoming-public` | Public | `limit?` min `1`, max `100` | upcoming public events |
| GET | `/api/events` | admin/reviewer | `date_from?`, `date_to?`, `status?`, `limit?`, `offset=0` | list of events |
| POST | `/api/events` | admin | `{ title, description?, starts_at, ends_at }` | event |
| GET | `/api/events/{event_id}` | admin/reviewer | None | event |
| GET | `/api/events/{event_id}/attendance` | admin/reviewer | None | event attendance |
| PATCH | `/api/events/{event_id}` | admin | `{ title?, description?, starts_at?, ends_at?, is_active? }` | event |
| DELETE | `/api/events/{event_id}` | admin | None | event |

Event fields: `id`, `title`, `description`, `starts_at`, `ends_at`, `is_active`, `created_by`, `created_at`, `updated_at`.

Event attendance fields: `event_id`, `title`, `description`, `starts_at`, `ends_at`, `is_active`, `total_logs`, `total_recognized_employees`, `present_count`, `pending_count`, `unknown_count`, `rejected_count`, `attendees`.

Important: the correct public active-events endpoint is `/api/events/list-public`. The older active-public event path is not available in current code.

## 15. Unknown Queue

| Method | Path | Auth | Request | Response |
| :----- | :--- | :--- | :------ | :------- |
| GET | `/api/unknown-queue` | admin/reviewer | `event_id?`, `meeting_id?`, `event_scope?`, `default_event_only=false` | list of unknown queue items |
| POST | `/api/unknown-queue/{queue_id}/assign` | admin/reviewer | `{ employee_id }` | common action response |
| POST | `/api/unknown-queue/{queue_id}/create` | admin/reviewer | `multipart/form-data`: `full_name`, `employee_code`, optional `avatar`, optional `vector_images[]` | common action response |
| POST | `/api/unknown-queue/{queue_id}/reject` | admin/reviewer | None | common action response |

Unknown queue item fields: `id`, `camera_id`, `event_id`, `event_title`, `meeting_id`, `meeting_title`, `image_path`, `image_url`, `attempt_count`, `first_seen_at`, `last_seen_at`, `face_quality`.

Unknown queue filter rules:

- Use either `event_id`, `meeting_id`, or `event_scope`, not multiple scopes at once.
- `event_scope` supports `default` and `inactive`.
- `default_event_only=true` is treated as `event_scope=default`.

Known gap: resolving unknown queue can link/create employee data, but meeting attendance is not yet refreshed from that resolution.

## 16. Recognition Logs

| Method | Path | Auth | Query | Response |
| :----- | :--- | :--- | :---- | :------- |
| GET | `/api/recognition-logs` | admin/reviewer | `date_from?`, `date_to?`, `camera_id?`, `event_id?`, `meeting_id?`, `employee_id?`, `result_label?`, `final_label?`, `include_pending=false`, `limit=100` | list of recognition log items |
| GET | `/api/recognition-logs/recent-public` | Public | `camera_id?`, `event_id?`, `meeting_id?`, `default_event_only=false`, `limit=20` | list of recognition log items |

Recognition log item fields: `id`, `camera_id`, `event_id`, `event_title`, `meeting_id`, `meeting_title`, `captured_at`, `face_image_path`, `face_image_url`, `result_label`, `top_score`, `employee_id`, `employee_name`, `final_label`, `resolved_at`.

## 17. Settings

| Method | Path | Auth | Request | Response |
| :----- | :--- | :--- | :------ | :------- |
| GET | `/api/settings` | admin | None | runtime settings |
| PATCH | `/api/settings` | admin | any subset of runtime settings | runtime settings |
| POST | `/api/settings/reset` | admin | None | runtime settings |

Runtime settings fields: `sure_threshold`, `review_low`, `gap_min`, `upsert_score_max`, `upsert_min_vecs`, `dedup_threshold`, `image_retention_days`, `recognition_log_cooldown_minutes`, `event_tablet_lookahead_minutes`.

## 18. Cleanup

| Method | Path | Auth | Request | Response |
| :----- | :--- | :--- | :------ | :------- |
| POST | `/api/cleanup/run` | admin | None | cleanup summary |

Cleanup summary fields: `success`, `deleted_recognition_log_images`, `deleted_resolved_unknown_queue`, `deleted_orphan_qdrant_points`, `deleted_unreferenced_files`, `auto_rejected_pending_recognition_logs`, `deleted_rejected_recognition_logs`, `deleted_read_notifications`, `deleted_empty_storage_dirs`, `retention_days`.

## 19. Export

| Method | Path | Auth | Body | Response |
| :----- | :--- | :--- | :--- | :------- |
| POST | `/api/export/attendance` | admin | `{ date_from?, date_to?, employee_id?, status?, format="csv" }` | CSV |
| POST | `/api/export/recognition-logs` | admin | `{ date_from?, date_to?, employee_id?, camera_id?, event_id?, result_label?, final_label?, format="csv" }` | CSV |
| POST | `/api/export/employees` | admin | `{ status?, format="csv" }` | CSV |

Note: `/api/attendance/export` also exists and exports attendance CSV. Prefer `/api/export/attendance` for the consolidated export module.

## 20. Complete Route Index

```text
GET    /health
POST   /api/auth/login
POST   /api/auth/refresh
POST   /api/recognition
POST   /api/recognition/confirm
GET    /api/me/profile
PATCH  /api/me/profile
PATCH  /api/me/password
GET    /api/me/recognition-logs/today
GET    /api/me/attendance
POST   /api/me/attendance/absence-request
GET    /api/me/notifications
GET    /api/me/notifications/unread-count
PATCH  /api/me/notifications/{notification_id}/read
POST   /api/me/notifications/read-all
POST   /api/me/meetings/{meeting_id}/checkin
POST   /api/me/meetings/{meeting_id}/checkout
POST   /api/me/meetings/{meeting_id}/absence-request
GET    /api/attendance
GET    /api/attendance/today
GET    /api/attendance/report
POST   /api/attendance/export
PATCH  /api/attendance/{record_id}
GET    /api/dashboard/stats
GET    /api/dashboard/attendance-trend
GET    /api/dashboard/recognition-activity
GET    /api/dashboard/late-arrivals
GET    /api/dashboard/camera-status
GET    /api/employees/active-public
GET    /api/employees
POST   /api/employees
DELETE /api/employees/{emp_id}
POST   /api/employees/{emp_id}/reactivate
POST   /api/employees/{emp_id}/anonymize
PATCH  /api/employees/{emp_id}/avatar
GET    /api/employees/{emp_id}/vectors
POST   /api/employees/{emp_id}/vectors
DELETE /api/employees/{emp_id}/vectors/{vec_id}
GET    /api/employees/{emp_id}/recognition-logs
GET    /api/employees/{emp_id}/account
POST   /api/employees/{emp_id}/account
PATCH  /api/users/{user_id}/password
PATCH  /api/users/{user_id}/status
GET    /api/cameras
POST   /api/cameras
PATCH  /api/cameras/{camera_id}
PATCH  /api/cameras/{camera_id}/status
GET    /api/meetings/list-public
GET    /api/meetings
POST   /api/meetings
GET    /api/meetings/{meeting_id}
PATCH  /api/meetings/{meeting_id}
DELETE /api/meetings/{meeting_id}
POST   /api/meetings/{meeting_id}/complete
POST   /api/meetings/{meeting_id}/participants
DELETE /api/meetings/{meeting_id}/participants/{emp_id}
GET    /api/meetings/{meeting_id}/attendance
GET    /api/events/list-public
GET    /api/events/upcoming-public
GET    /api/events
POST   /api/events
GET    /api/events/{event_id}
GET    /api/events/{event_id}/attendance
PATCH  /api/events/{event_id}
DELETE /api/events/{event_id}
GET    /api/unknown-queue
POST   /api/unknown-queue/{queue_id}/assign
POST   /api/unknown-queue/{queue_id}/create
POST   /api/unknown-queue/{queue_id}/reject
GET    /api/recognition-logs
GET    /api/recognition-logs/recent-public
GET    /api/settings
PATCH  /api/settings
POST   /api/settings/reset
POST   /api/cleanup/run
POST   /api/export/attendance
POST   /api/export/recognition-logs
POST   /api/export/employees
```
