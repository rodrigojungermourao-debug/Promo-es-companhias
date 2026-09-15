from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./promocoes.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Promocao(Base):
  __tablename__ = "promocoes"

  id = Column(Integer, primary_key=True, index=True)
  titulo = Column(String, nullable=False)
  link = Column(String, nullable=False)
  programa = Column(String, default="Geral")
  imagem = Column(String, nullable=True)  # link da capa
  data_coleta = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)
