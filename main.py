from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from database import SessionLocal, Promocao
import scraper

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/")
def index(request: Request, programa: str = None):
    db = SessionLocal()
    total = db.query(Promocao).count()
    if total == 0:
        scraper.coletar_promocoes()

    query = db.query(Promocao)
    if programa:
        query = query.filter(Promocao.programa == programa)
        
    promocoes = query.order_by(Promocao.id.desc()).limit(80).all()
    db.close()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"promocoes": promocoes, "programa_ativo": programa}
    )

@app.get("/passagens")
def passagens(request: Request, apenas_recomendadas: bool = False):
    db = SessionLocal()
    query = db.query(Promocao)

    termos = ["passag", "voo", "aéreo", "aereo", "tarifa", "trecho", "ida e volta", "ida"]
    todas = query.order_by(Promocao.id.desc()).all()
    
    lista = [p for p in todas if any(t in p.titulo.lower() for t in termos)]
    
    if apenas_recomendadas:
        lista = [p for p in lista if p.vale_a_pena]

    db.close()
    return templates.TemplateResponse(
        request=request,
        name="passagens.html",
        context={"passagens": lista, "apenas_recomendadas": apenas_recomendadas}
    )

@app.get("/atualizar")
def atualizar(background_tasks: BackgroundTasks):
    background_tasks.add_task(scraper.coletar_promocoes)
    return RedirectResponse(url="/", status_code=303)
