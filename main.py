import urllib.parse
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
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
    apenas_letras = "".join([c for c in t if c.isalpha()])
    return apenas_letras[:3].upper() if len(apenas_letras) >= 3 else "RIO"

def estimar_preco_medio(origem_iata, destino_iata):
    rotas_nordeste = ["FOR", "REC", "SSA", "NAT", "MCZ"]
    rotas_internacionais = ["BUE", "SCL", "MVD", "MIA", "MCO", "LIS"]
    
    if destino_iata in rotas_nordeste or origem_iata in rotas_nordeste:
        return "R$ 680", "~22.000 milhas"
    elif destino_iata in rotas_internacionais:
        return "R$ 1.850", "~65.000 milhas"
    else:
        return "R$ 420", "~14.000 milhas"

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
    origem_clean = origem.strip()
    destino_clean = destino.strip()
    
    orig_iata = obter_codigo_iata(origem_clean)
    dest_iata = obter_codigo_iata(destino_clean)

    preco_medio_reais, preco_medio_milhas = estimar_preco_medio(orig_iata, dest_iata)

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
            "preco_medio_reais": preco_medio_reais,
            "preco_medio_milhas": preco_medio_milhas,
            "link_gf": link_google_flights
        }
    )

@app.get("/atualizar")
def atualizar(background_tasks: BackgroundTasks):
    background_tasks.add_task(scraper.coletar_promocoes)
    return RedirectResponse(url="/", status_code=303)
