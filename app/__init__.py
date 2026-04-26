from app.database.session import Base
from app.models.user import User
from app.models.well import Well
from app.models.petrophysical_file import PetrophysicalFile, CurveData
from app.models.audit_log import AuditLog
from app.models.analysis_result import AnalysisResult # تأكد من اسم الملف

# هذه الخطوة تجبر SQLAlchemy على تسجيل كل الجداول فوراً
__all__ = ["Base", "User", "Well", "PetrophysicalFile", "CurveData", "AuditLog", "AnalysisResult"]