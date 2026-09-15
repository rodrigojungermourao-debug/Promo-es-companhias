import os
from database import Promocao, SessionLocal
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from scraper import coletar_promocoes
import uvicorn

app = FastAPI(title="Monitor de Milhas")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
  coletar_promocoes()

  db = SessionLocal()
  promocoes = (
      db.query(Promocao).order_by(Promocao.data_coleta.desc()).limit(30).all()
  )
  db.close()

  return templates.TemplateResponse(
      request=request,
      name="index.html",
      context={"promocoes": promocoes},
  )


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 8000))
  uvicorn.run("main:app", host="0.0.0.0", port=port)
  