from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.session import Base
import enum
import uuid
import datetime

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"

class User(Base):
    __tablename__ = "users"

    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4())) 
    display_name = Column(String) 
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default=UserRole.USER.value) # استخدام Enum أفضل
    avatar_url = Column(String, nullable=True)
    
    # التوقيت (مرة واحدة وبشكل صحيح)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # العلاقات (تأكدي أن كلاس Well و AuditLog معرفين في ملفاتهم)
    wells = relationship("Well", back_populates="owner", lazy="select")
    audit_logs = relationship("AuditLog", back_populates="user", lazy="select")

   
    #def __repr__(self):
        #return f"<User(id={self.id}, username={self.username}, role={self.role})>"