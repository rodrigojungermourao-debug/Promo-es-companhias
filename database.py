from sqlalchemy import create_engine, Column, Integer, String, Boolean
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

Base.metadata.create_all(bind=engine)
