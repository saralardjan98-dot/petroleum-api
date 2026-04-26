from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# --- 1. استيراد الـ Models والـ Base ---
# تأكدي أن المسار يطابق مشروعك (app.database.session و app.models.user)
from app.database.session import Base
from app.models.user import User 
# 

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- 2. ربط الـ Metadata ---
# هذا هو السطر الذي يسمح لـ Alembic برؤية جداولك وتوليد التعديلات تلقائياً
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = "postgresql://postgres:lardjan098@localhost/petroleum_mydb"
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    # --- 3. ضبط الرابط للـ Online Mode ---
    # نقوم بإجبار Alembic على استخدام الرابط الصحيح حتى لو لم يجده في alembic.ini
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = "postgresql://postgres:lardjan098@localhost/petroleum_mydb"
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()