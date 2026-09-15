from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine(
    "sqlite:///promocoes.db", connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Promocao(Base):
  __tablename__ = "promocoes"

  id = Column(Integer, primary_key=True, index=True)
  titulo = Column(String, unique=True, index=True)
  link = Column(String)
  programa = Column(String)
  data_coleta = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)