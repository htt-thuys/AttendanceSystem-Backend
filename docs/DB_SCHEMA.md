# Database Schema

> PostgreSQL: ORM models under `infrastructure/database/models/`
> Qdrant: synchronized 512-d vector embeddings from the `face_vectors` table
> Minimum Qdrant payload: `employee_id`, `face_vec_id`, `is_active`

## Tables

### `cameras` - Camera
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | autoincrement |
| `location` | Text | nullable |
| `is_active` | Boolean | default true |

### `employees` - Employee
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | autoincrement |
| `full_name` | Text | |
| `employee_code` | String(50) unique | |
| `avatar_path` | Text | nullable, current avatar image |
| `status` | String(20) | default `active`; `active`, `inactive`, `deleted` |
| `metadata` | JSONB | default `{}` |
| `created_at` | DateTime | default now() |
| `created_by` | Integer FK | references `users.id`, nullable |

### `users` - User
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | autoincrement |
| `username` | String(50) unique | primary login identifier |
| `email` | Text unique | nullable optional metadata |
| `password_hash` | Text | |
| `role` | String(20) | default `employee` |
| `is_active` | Boolean | default true |
| `employee_id` | Integer FK | references `employees.id`, nullable |
| `created_at` | DateTime | default now() |

### `face_vectors` - FaceVector
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | autoincrement |
| `employee_id` | Integer FK | references `employees.id` |
| `qdrant_point_id` | Integer unique | Qdrant point ID |
| `source` | String(20) | nullable |
| `source_image_path` | Text | source image used for this vector |
| `quality_score` | Float | nullable |
| `score_at_create` | Float | nullable |
| `is_active` | Boolean | default true |
| `created_at` | DateTime | default now() |

Qdrant synchronization notes:
- Each active `face_vectors` row should have a corresponding point in Qdrant.
- `qdrant_point_id` is the point ID in Qdrant.
- The point payload uses `face_vec_id` to point back to `face_vectors.id`.
- When an employee is deactivated or reactivated, the backend updates the Qdrant payload `is_active`.
- When an admin deletes a vector or anonymizes an employee, the backend permanently deletes the `face_vectors` row and matching Qdrant point.

### `recognition_logs` - RecognitionLog
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | autoincrement |
| `camera_id` | Integer FK | references `cameras.id`, nullable |
| `event_id` | Integer FK | references `events.id`, nullable |
| `meeting_id` | Integer FK | references `meetings.id`, nullable |
| `captured_at` | DateTime | default now() |
| `face_image_path` | Text | nullable, retained according to `image_retention_days` |
| `result_label` | String(10) | nullable: `sure`, `review`, `unknown` |
| `top_score` | Float | nullable |
| `employee_id` | Integer FK | references `employees.id`, nullable |
| `final_label` | String(20) | nullable |
| `resolved_at` | DateTime | nullable |
| `resolved_by` | Integer FK | references `users.id`, nullable |

### `events` - Event
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | autoincrement |
| `title` | Text | event display name |
| `description` | Text | nullable |
| `starts_at` | DateTime | event start |
| `ends_at` | DateTime | event end |
| `is_active` | Boolean | default true |
| `created_by` | Integer FK | references `users.id` |
| `created_at` | DateTime | default now() |
| `updated_at` | DateTime | default now() |

Constraints:
- INDEX(`starts_at`)
- INDEX(`ends_at`)
- INDEX(`is_active`, `starts_at`, `ends_at`)

### `attendance_records` - AttendanceRecord
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | autoincrement |
| `employee_id` | Integer FK | references `employees.id` |
| `date` | Date | attendance date |
| `check_in_time` | DateTime | nullable |
| `check_out_time` | DateTime | nullable |
| `check_in_log_id` | Integer FK | references `recognition_logs.id`, nullable |
| `check_out_log_id` | Integer FK | references `recognition_logs.id`, nullable |
| `status` | String(20) | default `absent` |
| `work_hours` | Float | nullable |
| `note` | Text | nullable |
| `created_at` | DateTime | default now() |
| `updated_at` | DateTime | default now() |

Constraints:
- UNIQUE(`employee_id`, `date`)
- INDEX(`date`)
- INDEX(`employee_id`, `date`)

### `work_schedules` - WorkSchedule
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | autoincrement |
| `name` | String(100) | schedule name |
| `start_time` | Time | start time |
| `end_time` | Time | end time |
| `late_threshold_minutes` | Integer | allowed late threshold in minutes |
| `is_default` | Boolean | default false |
| `created_at` | DateTime | default now() |

### `meetings` - Meeting
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | autoincrement |
| `title` | Text | |
| `description` | Text | nullable |
| `scheduled_start` | DateTime | |
| `scheduled_end` | DateTime | nullable |
| `actual_start` | DateTime | nullable |
| `actual_end` | DateTime | nullable |
| `location` | Text | nullable |
| `camera_id` | Integer FK | references `cameras.id`, nullable |
| `status` | String(20) | default `scheduled` |
| `created_by` | Integer FK | references `users.id` |
| `created_at` | DateTime | default now() |
| `updated_at` | DateTime | default now() |

Constraints:
- INDEX(`scheduled_start`)
- INDEX(`status`)

### `meeting_participants` - MeetingParticipant
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | autoincrement |
| `meeting_id` | Integer FK | references `meetings.id` with cascade delete |
| `employee_id` | Integer FK | references `employees.id` |
| `status` | String(20) | default `invited` |
| `check_in_time` | DateTime | nullable |
| `check_in_log_id` | Integer FK | references `recognition_logs.id`, nullable |
| `check_out_time` | DateTime | nullable |
| `check_out_log_id` | Integer FK | references `recognition_logs.id`, nullable |
| `note` | Text | nullable |

Constraints:
- UNIQUE(`meeting_id`, `employee_id`)
- INDEX(`meeting_id`)
- INDEX(`employee_id`)

### `notifications` - Notification
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | autoincrement |
| `user_id` | Integer FK | references `users.id` |
| `type` | String(30) | notification type |
| `title` | Text | title |
| `message` | Text | nullable |
| `is_read` | Boolean | default false |
| `data` | JSONB | nullable |
| `created_at` | DateTime | default now() |
| `read_at` | DateTime | nullable |

Constraints:
- INDEX(`user_id`, `is_read`)
- INDEX(`user_id`, `created_at`)

### `unknown_queue` - UnknownQueue
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | autoincrement |
| `camera_id` | Integer FK | references `cameras.id`, nullable |
| `event_id` | Integer FK | references `events.id`, nullable |
| `meeting_id` | Integer FK | references `meetings.id`, nullable |
| `image_path` | Text | current representative image, always matching `vector` |
| `vector` | ARRAY(Float) | 512-d vector |
| `face_quality` | Float | nullable, face-image quality score for selecting better images |
| `attempt_count` | Integer | default 1 |
| `first_seen_at` | DateTime | default now() |
| `last_seen_at` | DateTime | default now() |
| `resolved_at` | DateTime | nullable |
| `resolved_by` | Integer FK | references `users.id`, nullable |

### `admin_logs` - AdminLog
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | autoincrement |
| `admin_id` | Integer FK | references `users.id` |
| `action` | String(30) | nullable |
| `target_type` | String(30) | nullable |
| `target_id` | Integer | |
| `note` | Text | nullable |
| `created_at` | DateTime | default now() |

### `system_settings` - SystemSetting
| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | autoincrement |
| `key` | String(100) unique | runtime setting name |
| `value` | Text | override value stored as a string |
| `updated_at` | DateTime | default now() |
| `updated_by` | Integer FK | references `users.id`, nullable |

Runtime keys currently used:
- `sure_threshold`
- `review_low`
- `gap_min`
- `upsert_score_max`
- `upsert_min_vecs`
- `dedup_threshold`
- `image_retention_days`
- `recognition_log_cooldown_minutes`
- `event_tablet_lookahead_minutes`

## Relationships

```text
users 1--1 employees
users 1--N employees (created_by)
cameras 1--N recognition_logs
cameras 1--N meetings
cameras 1--N unknown_queue
events 1--N recognition_logs
events 1--N unknown_queue
meetings 1--N recognition_logs
meetings 1--N unknown_queue
employees 1--N face_vectors
employees 1--N recognition_logs
employees 1--N meeting_participants
meetings 1--N meeting_participants
users 1--N unknown_queue (resolved_by)
users 1--N recognition_logs (resolved_by)
users 1--N admin_logs
users 1--N system_settings (updated_by)
users 1--N meetings (created_by)
users 1--N events (created_by)
recognition_logs 1--N meeting_participants (check_in_log_id)
recognition_logs 1--N meeting_participants (check_out_log_id)
users 1--N notifications
```

## Delete And Anonymize Rules

- Soft-delete employee: set `employees.status = inactive`, lock the linked account with `users.is_active = false`, disable all vectors in the DB and Qdrant, and allow reactivation.
- Reactivate employee: only applies to `status = inactive`; re-enables the linked account and remaining vectors.
- Anonymize employee: set `employees.status = deleted`, keep `employees.id` and `users.id` for FK/history preservation, overwrite PII, lock the account, delete avatar, delete that employee's recognition-log images, and permanently delete `face_vectors` rows and Qdrant points.
- Deleted employees cannot be reactivated.
