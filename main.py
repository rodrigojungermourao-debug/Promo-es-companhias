from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import SessionLocal, Promocao
import scraper

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Executa a varredura a cada 30 minutos em segundo plano
    scheduler.add_job(scraper.coletar_promocoes, "interval", minutes=30)
    
    # Envia o resumo matinal no Telegram todos os dias às 08:30
    scheduler.add_job(
        scraper.enviar_resumo_diario_telegram,
        CronTrigger(hour=8, minute=30)
    )
    
    scheduler.start()
    print("[SCHEDULER] Agendador de tarefas em segundo plano iniciado com sucesso!")
    
    yield
    
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

@app.get("/")
def index(request: Request, programa: str = None):
    db = SessionLocal()
    total = db.query(Promocao).count()
    if total == 0:
        scraper.coletar_promocoes()

    novos = {
        "Todos": 0, "Livelo": 0, "Esfera": 0, 
        "Smiles": 0, "LATAM Pass": 0, "Azul": 0, "Premmia": 0
    }

    try:
        limite_novas = datetime.utcnow() - timedelta(hours=24)
        contagens = (
            db.query(Promocao.programa, func.count(Promocao.id))
            .filter((Promocao.data_criacao >= limite_novas) | (Promocao.data_criacao.is_(None)))
            .group_by(Promocao.programa)
            .all()
        )
        for prog, total_qtd in contagens:
            if prog:
                novos[prog] = total_qtd
        novos["Todos"] = sum(v for k, v in novos.items() if k != "Todos")
    except Exception as e:
        print(f"[ERRO CONTADORES]: {e}")
        db.rollback()

    query = db.query(Promocao)
    if programa:
        query = query.filter(Promocao.programa == programa)
        
    promocoes = query.order_by(Promocao.id.desc()).limit(80).all()
    db.close()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "promocoes": promocoes,
            "programa_ativo": programa,
            "novos": novos
        }
    )

@app.get("/disparar-todas-hoje")
def disparar_todas_hoje(background_tasks: BackgroundTasks):
    background_tasks.add_task(scraper.enviar_todas_promocoes_hoje)
    return {"mensagem": "Disparo de TODAS as promocoes cadastradas acionado em segundo plano!"}

@app.get("/testar-resumo")
def testar_resumo(background_tasks: BackgroundTasks):
    background_tasks.add_task(scraper.enviar_resumo_diario_telegram)
    return {"mensagem": "Disparo do resumo diario acionado em segundo plano!"}

@app.get("/atualizar")
def atualizar(background_tasks: BackgroundTasks):
    background_tasks.add_task(scraper.coletar_promocoes)
    return RedirectResponse(url="/", status_code=303)
