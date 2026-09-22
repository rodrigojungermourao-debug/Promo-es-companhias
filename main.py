import urllib.parse
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
    scheduler.add_job(scraper.coletar_promocoes, "interval", minutes=30)
    scheduler.add_job(
        scraper.enviar_resumo_diario_telegram,
        CronTrigger(hour=8, minute=30)
    )
    scheduler.start()
    print("[SCHEDULER] Agendador iniciado com sucesso!")
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

AEROPORTOS_IATA = {
    "rio": "RIO", "rio de janeiro": "RIO", "gig": "GIG", "sdu": "SDU",
    "fortaleza": "FOR", "for": "FOR",
    "sao paulo": "SAO", "são paulo": "SAO", "sp": "SAO", "gru": "GRU", "cgh": "CGH",
    "brasilia": "BSB", "brasília": "BSB", "bsb": "BSB",
    "salvador": "SSA", "ssa": "SSA",
    "recife": "REC", "rec": "REC",
    "belo horizonte": "BHZ", "bh": "BHZ", "cnf": "CNF",
    "porto alegre": "POA", "poa": "POA",
    "curitiba": "CWB", "cwb": "CWB",
    "florianopolis": "FLN", "florianópolis": "FLN", "fln": "FLN",
    "natal": "NAT", "nat": "NAT",
    "maceio": "MCZ", "maceió": "MCZ", "mcz": "MCZ",
    "buenos aires": "BUE", "bue": "BUE",
    "santiago": "SCL", "scl": "SCL",
    "montevideo": "MVD", "montevidéu": "MVD", "mvd": "MVD",
    "miami": "MIA", "mia": "MIA",
    "orlando": "MCO", "mco": "MCO",
    "lisboa": "LIS", "lis": "LIS"
}

def obter_codigo_iata(texto):
    t = texto.lower().strip()
    for chave, iata in AEROPORTOS_IATA.items():
        if chave in t:
            return iata
    letras = "".join([c for c in t if c.isalpha()])
    return letras[:3].upper() if len(letras) >= 3 else "RIO"

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

@app.get("/passagens")
def tela_passagens(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="passagens.html",
        context={
            "buscou": False,
            "origem": "",
            "destino": "",
            "data_ida": "",
            "data_volta": "",
            "voos": []
        }
    )

@app.get("/passagens/buscar")
def buscar_voos(request: Request, origem: str = "São Paulo (GRU)", destino: str = "Recife (REC)", data_ida: str = "", data_volta: str = ""):
    orig_clean = origem.replace("(GRU)", "").replace("(RIO)", "").strip()
    dest_clean = destino.replace("(REC)", "").replace("(FOR)", "").strip()
    
    orig_iata = obter_codigo_iata(orig_clean)
    dest_iata = obter_codigo_iata(dest_clean)

    if data_volta:
        query_gf = f"Flights to {dest_iata} from {orig_iata} on {data_ida} through {data_volta}"
    else:
        query_gf = f"Flights to {dest_iata} from {orig_iata} on {data_ida} one way"
        
    link_google_flights = f"https://www.google.com/travel/flights?q={urllib.parse.quote(query_gf)}"

    # Gera a listagem no formato idêntico ao Google Flights
    rota_label = f"{orig_iata}–{dest_iata}"
    voos = [
        {
            "cia": "GOL",
            "operado_por": "Gol",
            "cor_logo": "text-orange-500",
            "horario_partida": "09:05",
            "horario_chegada": "12:15",
            "duracao": "3h 10 min",
            "rota": rota_label,
            "paradas": "Sem escalas",
            "emissoes": "174 kg CO2e",
            "emissoes_detalhe": "+7% emissões",
            "preco": "974"
        },
        {
            "cia": "GOL",
            "operado_por": "Gol",
            "cor_logo": "text-orange-500",
            "horario_partida": "13:25",
            "horario_chegada": "16:30",
            "duracao": "3h 05 min",
            "rota": rota_label,
            "paradas": "Sem escalas",
            "emissoes": "174 kg CO2e",
            "emissoes_detalhe": "+7% emissões",
            "preco": "974"
        },
        {
            "cia": "GOL",
            "operado_por": "Gol",
            "cor_logo": "text-orange-500",
            "horario_partida": "22:05",
            "horario_chegada": "01:15+1",
            "duracao": "3h 10 min",
            "rota": rota_label,
            "paradas": "Sem escalas",
            "emissoes": "174 kg CO2e",
            "emissoes_detalhe": "+7% emissões",
            "preco": "974"
        },
        {
            "cia": "LATAM",
            "operado_por": "Latam Airlines Brasil",
            "cor_logo": "text-red-700",
            "horario_partida": "23:50",
            "horario_chegada": "02:55+1",
            "duracao": "3h 05 min",
            "rota": rota_label,
            "paradas": "Sem escalas",
            "emissoes": "172 kg CO2e",
            "emissoes_detalhe": "+6% emissões",
            "preco": "995"
        },
        {
            "cia": "AZUL",
            "operado_por": "Azul Linhas Aéreas",
            "cor_logo": "text-blue-600",
            "horario_partida": "06:15",
            "horario_chegada": "09:30",
            "duracao": "3h 15 min",
            "rota": rota_label,
            "paradas": "Sem escalas",
            "emissoes": "168 kg CO2e",
            "emissoes_detalhe": "+3% emissões",
            "preco": "1.049"
        }
    ]

    return templates.TemplateResponse(
        request=request,
        name="passagens.html",
        context={
            "buscou": True,
            "origem": origem,
            "destino": destino,
            "orig_iata": orig_iata,
            "dest_iata": dest_iata,
            "data_ida": data_ida,
            "data_volta": data_volta,
            "link_gf": link_google_flights,
            "voos": voos
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
