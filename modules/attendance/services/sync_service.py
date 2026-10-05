"""Synchronization and auto-generated attendance services."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from modules.attendance import repository
from modules.attendance.helpers import LOCAL_TZ, compute_work_hours, derive_status


async def record_auto_attendance(
    db: AsyncSession,
    employee_id: int,
    recognition_log_id: int | None,
    captured_at: datetime,
) -> bool:
    """Ghi nhận điểm danh tự động sau khi AI nhận diện thành công."""
    local_dt = captured_at.astimezone(LOCAL_TZ) if captured_at.tzinfo else captured_at
    today = local_dt.date()

    schedule = await repository.get_default_schedule(db)
    existing = await repository.get_attendance_record(db, employee_id, today)

    if existing:
        if existing.check_in_time is None:
            existing.check_in_time = captured_at
            existing.check_in_log_id = recognition_log_id
            existing.status = derive_status(today, schedule, captured_at)
    else:
        await repository.create_attendance_record(
            db=db,
            employee_id=employee_id,
            target_date=today,
            check_in_time=captured_at,
            check_out_time=None,
            check_in_log_id=recognition_log_id,
            check_out_log_id=None,
            status=derive_status(today, schedule, captured_at),
            work_hours=None,
        )
    return True


async def ensure_attendance_records(
    db: AsyncSession,
    date_from: date | None,
    date_to: date | None,
    employee_id: int | None,
) -> None:
    """Đảm bảo có dữ liệu điểm danh cho khoảng ngày yêu cầu."""
    normalized_from, normalized_to = normalize_date_range(date_from, date_to)
    if normalized_from is None or normalized_to is None:
        return
    if normalized_from > normalized_to:
        raise HTTPException(
            status_code=400,
            detail="Ngày bắt đầu phải trước hoặc bằng ngày kết thúc",
        )

    schedule = await repository.get_default_schedule(db)
    target_employees = await resolve_target_employees(db, employee_id)
    employee_ids = [employee.id for employee in target_employees]

    all_logs = await repository.list_confirmed_logs_for_date_range(
        db,
        employee_ids,
        normalized_from,
        normalized_to,
    )
    all_records = await repository.list_existing_attendance_records(
        db,
        employee_ids,
        normalized_from,
        normalized_to,
    )

    logs_by_key = group_logs_by_employee_date(all_logs)
    records_by_key = {(record.employee_id, record.date): record for record in all_records}

    now_ref = datetime.now(LOCAL_TZ)
    current_date = normalized_from
    while current_date <= normalized_to:
        for employee in target_employees:
            await upsert_daily_record(
                db=db,
                employee_id=employee.id,
                target_date=current_date,
                schedule=schedule,
                logs=logs_by_key.get((employee.id, current_date), []),
                existing=records_by_key.get((employee.id, current_date)),
                now_ref=now_ref,
            )
        current_date += timedelta(days=1)

    await db.commit()


def normalize_date_range(
    date_from: date | None,
    date_to: date | None,
) -> tuple[date | None, date | None]:
    """Chuẩn hóa khoảng ngày: thiếu một đầu thì dùng đầu còn lại; thiếu cả hai thì dùng today."""
    if date_from is None and date_to is None:
        today = date.today()
        return today, today
    if date_from is None:
        return date_to, date_to
    if date_to is None:
        return date_from, date_from
    return date_from, date_to


def group_logs_by_employee_date(logs: list[Any]) -> dict[tuple[int, date], list[Any]]:
    """Group confirmed logs theo (employee_id, local_date)."""
    grouped: dict[tuple[int, date], list[Any]] = defaultdict(list)
    for log in logs:
        local_dt = log.captured_at.astimezone(LOCAL_TZ) if log.captured_at.tzinfo else log.captured_at
        grouped[(log.employee_id, local_dt.date())].append(log)
    return grouped


async def upsert_daily_record(
    db: AsyncSession,
    employee_id: int,
    target_date: date,
    schedule,
    logs: list[Any],
    existing,
    now_ref: datetime,
) -> None:
    """Tạo hoặc cập nhật bản ghi điểm danh cho 1 nhân viên trong 1 ngày."""
    check_in_log = logs[0] if logs else None
    check_in_time = check_in_log.captured_at if check_in_log else None
    work_hours = compute_work_hours(check_in_time, target_date, now_ref)
    status = derive_status(target_date, schedule, check_in_time)
    log_id = check_in_log.id if check_in_log else None

    if existing:
        if existing.status == "excused" and check_in_time is None:
            return
        existing.check_in_time = check_in_time
        existing.check_out_time = None
        existing.check_in_log_id = log_id
        existing.check_out_log_id = None
        existing.status = status
        existing.work_hours = work_hours
        return

    await repository.create_attendance_record(
        db=db,
        employee_id=employee_id,
        target_date=target_date,
        check_in_time=check_in_time,
        check_out_time=None,
        check_in_log_id=log_id,
        check_out_log_id=None,
        status=status,
        work_hours=work_hours,
    )


async def resolve_target_employees(
    db: AsyncSession,
    employee_id: int | None,
) -> list:
    """Xác định danh sách nhân viên cần xử lý điểm danh."""
    if employee_id is None:
        return await repository.list_active_employees(db)

    employee = await repository.get_employee_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhân viên")
    return [employee]
