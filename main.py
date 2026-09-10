from typing import List, Optional
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Создаем файл базы данных SQLite на сервере
DATABASE_URL = "sqlite:///./proxies.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Описание таблицы прокси в базе данных
class ProxyModel(Base):
  __tablename__ = "proxies"

  id = Column(Integer, primary_key=True, index=True)
  name = Column(String, index=True)
  server = Column(String)
  port = Column(Integer)
  secret = Column(String)
  ping = Column(Integer, default=0)


# Создаем таблицу, если её еще нет
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Proxy Manager API with DB")

# Секретный пароль для админа (измени на свой сложный пароль)
ADMIN_SECRET_KEY = "my_super_secret_admin_token_123"


# Pydantic схема для валидации данных
class ProxyCreate(BaseModel):
  name: str
  server: str
  port: int
  secret: str
  ping: Optional[int] = 0


class ProxyResponse(ProxyCreate):
  id: int

  model_config = ConfigDict(from_attributes=True)


# Зависимость для получения сессии БД
def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()


# Корень для проверки, что сервер работает
@app.get("/")
def root():
  return {"message": "Proxy API работает!", "docs": "/docs"}


# 1. ПОЛУЧИТЬ СПИСОК ПРОКСИ (для всех пользователей)
@app.get("/proxies", response_model=List[ProxyResponse])
def get_proxies(db: Session = Depends(get_db)):
  return db.query(ProxyModel).all()


# 2. ДОБАВИТЬ ПРОКСИ (только для админа)
@app.post("/admin/add_proxy", response_model=ProxyResponse)
def add_proxy(
    proxy: ProxyCreate,
    x_admin_token: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
  if x_admin_token != ADMIN_SECRET_KEY:
    raise HTTPException(
        status_code=403, detail="Доступ запрещен: неверный админ-токен"
    )

  db_proxy = ProxyModel(
      name=proxy.name,
      server=proxy.server,
      port=proxy.port,
      secret=proxy.secret,
      ping=proxy.ping,
  )
  db.add(db_proxy)
  db.commit()
  db.refresh(db_proxy)
  return db_proxy


# 3. УДАЛИТЬ ПРОКСИ (только для админа)
@app.delete("/admin/delete_proxy/{proxy_id}")
def delete_proxy(
    proxy_id: int,
    x_admin_token: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
  if x_admin_token != ADMIN_SECRET_KEY:
    raise HTTPException(
        status_code=403, detail="Доступ запрещен: неверный админ-токен"
    )

  db_proxy = db.query(ProxyModel).filter(ProxyModel.id == proxy_id).first()
  if not db_proxy:
    raise HTTPException(status_code=404, detail="Прокси не найден")

  db.delete(db_proxy)
  db.commit()
  return {"status": "success", "message": f"Прокси ID {proxy_id} удален"}