from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from database import SessionLocal, Promocao
import scraper

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/")
def index(request: Request, programa: str = None):
    db = SessionLocal()
    query = db.query(Promocao)
    
    if programa:
        query = query.filter(Promocao.programa == programa)
        
    promocoes = query.order_by(Promocao.id.desc()).all()
    db.close()
    
    # Se o banco estiver vazio (ex: acabou de subir novo deploy), busca a primeira vez
    if not promocoes:
        scraper.coletar_promocoes()
        db = SessionLocal()
        promocoes = db.query(Promocao).order_by(Promocao.id.desc()).all()
        db.close()

    return templates.TemplateResponse("index.html", {"request": request, "promocoes": promocoes})

@app.get("/atualizar")
def atualizar():
    scraper.coletar_promocoes()
    return RedirectResponse(url="/", status_code=303)
