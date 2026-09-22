from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./promocoes.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Promocao(Base):
    __tablename__ = "promocoes"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, nullable=False)
    link = Column(String, unique=True, index=True, nullable=False)
    programa = Column(String, nullable=True)
    imagem = Column(String, nullable=True)
    vale_a_pena = Column(Boolean, default=False)
    preco_destaque = Column(String, nullable=True)
    data_criacao = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE promocoes ADD COLUMN data_criacao DATETIME"))
        conn.commit()
except Exception:
    pass
