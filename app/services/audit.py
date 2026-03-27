from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from typing import Optional, Dict, Any


def log_action(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    description: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None,
    status: str = "success",
) -> AuditLog:
    """Create an audit log entry."""
    log = AuditLog(
        action=action,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
        extra_data=extra_data,
        status=status,
    )
    db.add(log)
    db.flush()  # Don't commit here — let the caller manage transactions
    return log


# Action constants
class Actions:
    # Auth
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    REGISTER = "REGISTER"
    CHANGE_PASSWORD = "CHANGE_PASSWORD"

    # Wells
    CREATE_WELL = "CREATE_WELL"
    UPDATE_WELL = "UPDATE_WELL"
    DELETE_WELL = "DELETE_WELL"
    VIEW_WELL = "VIEW_WELL"

    # Files
    UPLOAD_FILE = "UPLOAD_FILE"
    DELETE_FILE = "DELETE_FILE"
    REPROCESS_FILE = "REPROCESS_FILE"

    # Results
    CREATE_RESULT = "CREATE_RESULT"
    UPDATE_RESULT = "UPDATE_RESULT"
    DELETE_RESULT = "DELETE_RESULT"

    # Admin
    UPDATE_USER = "UPDATE_USER"
    DEACTIVATE_USER = "DEACTIVATE_USER"
