import urllib.parse
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from database import SessionLocal, Promocao
import scraper

app = FastAPI()
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
            "data_volta": ""
        }
    )

@app.get("/passagens/buscar")
def buscar_voos(request: Request, origem: str = "", destino: str = "", data_ida: str = "", data_volta: str = ""):
    origem_clean = origem.replace("(RIO)", "").strip()
    destino_clean = destino.replace("(FOR)", "").strip()
    
    orig_iata = obter_codigo_iata(origem_clean)
    dest_iata = obter_codigo_iata(destino_clean)

    if data_volta:
        query_gf = f"Flights to {dest_iata} from {orig_iata} on {data_ida} through {data_volta}"
    else:
        query_gf = f"Flights to {dest_iata} from {orig_iata} on {data_ida} one way"
        
    link_google_flights = f"https://www.google.com/travel/flights?q={urllib.parse.quote(query_gf)}"

    return templates.TemplateResponse(
        request=request,
        name="passagens.html",
        context={
            "buscou": True,
            "origem": origem_clean,
            "destino": destino_clean,
            "orig_iata": orig_iata,
            "dest_iata": dest_iata,
            "data_ida": data_ida,
            "data_volta": data_volta,
            "link_gf": link_google_flights
        }
    )

@app.get("/atualizar")
def atualizar(background_tasks: BackgroundTasks):
    background_tasks.add_task(scraper.coletar_promocoes)
    return RedirectResponse(url="/", status_code=303)