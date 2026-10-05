"""Notification helpers for meeting invitations."""

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.email_sender import send_bulk_email
from modules.meetings import repository
from modules.meetings.helpers import build_meeting_invitation_email


async def notify_meeting_participants(
    db: AsyncSession,
    employee_ids: list[int],
    title: str,
    message: str,
    data: dict,
) -> None:
    """Tao notification noi bo va gui email moi hop."""
    users = await repository.list_users_by_employee_ids(
        db=db,
        employee_ids=employee_ids,
    )
    user_ids = [user.id for user in users]
    if user_ids:
        await repository.create_notifications(
            db=db,
            user_ids=user_ids,
            type_="meeting",
            title=title,
            message=message,
            data=data,
        )

    recipients = [user.email for user in users if user.email]
    if recipients:
        await send_bulk_email(
            recipients=recipients,
            subject=title,
            body=build_meeting_invitation_email(message, data),
        )
