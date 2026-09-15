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

def extrair_iata(texto):
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
    
    iata_origem = extrair_iata(origem_clean)
    iata_destino = extrair_iata(destino_clean)

    # 1. Google Flights
    if data_volta:
        query_gf = f"Flights to {iata_destino} from {iata_origem} on {data_ida} through {data_volta}"
    else:
        query_gf = f"Flights to {iata_destino} from {iata_origem} on {data_ida} one way"
    url_google_flights = f"https://www.google.com/travel/flights?q={urllib.parse.quote(query_gf)}"

    # 2. Kayak
    if data_volta:
        url_kayak = f"https://www.kayak.com.br/flights/{iata_origem}-{iata_destino}/{data_ida}/{data_volta}?sort=bestflight_a"
    else:
        url_kayak = f"https://www.kayak.com.br/flights/{iata_origem}-{iata_destino}/{data_ida}?sort=bestflight_a"

    # 3. Decolar
    if data_volta:
        url_decolar = f"https://www.decolar.com/passagens-aereas/buscar/ida-e-volta/{iata_origem}/{iata_destino}/{data_ida}/{data_volta}/1/0/0"
    else:
        url_decolar = f"https://www.decolar.com/passagens-aereas/buscar/somente-ida/{iata_origem}/{iata_destino}/{data_ida}/1/0/0"

    # 4. GOL / Smiles
    url_gol = f"https://www.smiles.com.br/passagens-aereas"

    # 5. LATAM Pass
    url_latam = f"https://latampass.latam.com/pt_br/promocoes"

    resultados = [
        {
            "companhia": "Google Flights (Comparador Geral)",
            "codigo": "GOO",
            "detalhes": f"Consulta simultânea de todas as companhias na rota ({iata_origem} ➔ {iata_destino})",
            "preco_reais": "Tempo Real",
            "preco_milhas": "Menor Tarifa",
            "melhor_custo": True,
            "link_direto": url_google_flights
        },
        {
            "companhia": "GOL Linhas Aéreas / Smiles",
            "codigo": "GOL",
            "detalhes": f"Cotação dinâmica Smiles para {iata_origem} ➔ {iata_destino} na data",
            "preco_reais": "Dinâmico",
            "preco_milhas": "Milhas Smiles",
            "melhor_custo": False,
            "link_direto": url_gol
        },
        {
            "companhia": "Kayak Metabusca",
            "codigo": "KAY",
            "detalhes": f"Rastreamento de agências online, bagagens e taxas em tempo real",
            "preco_reais": "Tempo Real",
            "preco_milhas": "Agências & Cias",
            "melhor_custo": False,
            "link_direto": url_kayak
        },
        {
            "companhia": "Decolar.com",
            "codigo": "DEC",
            "detalhes": f"Pacotes e passagens com taxas inclusas na rota {iata_origem} ➔ {iata_destino}",
            "preco_reais": "Em Reais",
            "preco_milhas": "Parcelamento",
            "melhor_custo": False,
            "link_direto": url_decolar
        },
        {
            "companhia": "LATAM Airlines / LATAM Pass",
            "codigo": "LAT",
            "detalhes": f"Resgate tarifário direto e pontos LATAM Pass",
            "preco_reais": "Dinâmico",
            "preco_milhas": "Pontos LATAM",
            "melhor_custo": False,
            "link_direto": url_latam
        }
    ]

    return templates.TemplateResponse(
        request=request,
        name="passagens.html",
        context={
            "buscou": True,
            "origem": origem_clean,
            "destino": destino_clean,
            "data_ida": data_ida,
            "data_volta": data_volta,
            "resultados": resultados
        }
    )

@app.get("/atualizar")
def atualizar(background_tasks: BackgroundTasks):
    background_tasks.add_task(scraper.coletar_promocoes)
    return RedirectResponse(url="/", status_code=303)
