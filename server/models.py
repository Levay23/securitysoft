from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import datetime
import os

Base = declarative_base()

class License(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    hwid = Column(String, nullable=True) # Se llena al activar
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True) # Fecha de vencimiento
    note = Column(String, nullable=True) # Cliente
    bot_name = Column(String, default="Unknown Bot") # Nombre del Bot

# Configuración de base de datos HÍBRIDA (Local: SQLite, Nube: PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Ajuste necesario para Heroku/Render si la URL viene como 'postgres://' (antiguo) en vez de 'postgresql://'
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL)
else:
    # Modo Local (SQLite)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "licenses.db")
    DATABASE_URL = f"sqlite:///{db_path}"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
