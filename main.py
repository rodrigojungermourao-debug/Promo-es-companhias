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

    # 1. Google Flights (Comparador em R$)
    if data_volta:
        query_gf = f"Flights to {dest_iata} from {orig_iata} on {data_ida} through {data_volta}"
    else:
        query_gf = f"Flights to {dest_iata} from {orig_iata} on {data_ida} one way"
    link_google_flights = f"https://www.google.com/travel/flights?q={urllib.parse.quote(query_gf)}"

    # 2. Deep Link Direto SMILES com Milhas ativadas
    # O parametro miles=true e tipoViagem=V forçam a exibicao em milhas
    link_smiles_milhas = f"https://www.smiles.com.br/passagens-aereas?from={orig_iata}&to={dest_iata}&departureDate={data_ida}&adults=1&miles=true"
    if data_volta:
        link_smiles_milhas += f"&returnDate={data_volta}"

    # 3. Deep Link LATAM Pass com busca de pontos
    link_latam_pontos = f"https://www.latamairlines.com/br/pt/ofertas-voos?origin={orig_iata}&destination={dest_iata}&outbound={data_ida}&redemption=true"
    if data_volta:
        link_latam_pontos += f"&inbound={data_volta}"

    # 4. Kayak para comparador geral
    if data_volta:
        link_kayak = f"https://www.kayak.com.br/flights/{orig_iata}-{dest_iata}/{data_ida}/{data_volta}?sort=bestflight_a"
    else:
        link_kayak = f"https://www.kayak.com.br/flights/{orig_iata}-{dest_iata}/{data_ida}?sort=bestflight_a"

    return templates.TemplateResponse(
        request=request,
        name="passagens.html",
        context={
            "buscou": True,
            "origem": origem_clean,
            "destino": destino_clean,
            "data_ida": data_ida,
            "data_volta": data_volta,
            "link_gf": link_google_flights,
            "link_smiles_milhas": link_smiles_milhas,
            "link_latam_pontos": link_latam_pontos,
            "link_kayak": link_kayak
        }
    )

@app.get("/atualizar")
def atualizar(background_tasks: BackgroundTasks):
    background_tasks.add_task(scraper.coletar_promocoes)
    return RedirectResponse(url="/", status_code=303)
