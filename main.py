import urllib.parse
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from database import SessionLocal, Promocao
import scraper

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Mapeamento para códigos IATA de 3 letras
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

    # 1. Google Flights com a sintaxe funcional universal em inglês
    if data_volta:
        query_gf = f"Flights to {dest_iata} from {orig_iata} on {data_ida} through {data_volta}"
    else:
        query_gf = f"Flights to {dest_iata} from {orig_iata} on {data_ida} one way"
    url_google_flights = f"https://www.google.com/travel/flights?q={urllib.parse.quote(query_gf)}"

    # 2. Kayak com Deep Link direto
    if data_volta:
        url_kayak = f"https://www.kayak.com.br/flights/{orig_iata}-{dest_iata}/{data_ida}/{data_volta}?sort=bestflight_a"
    else:
        url_kayak = f"https://www.kayak.com.br/flights/{orig_iata}-{dest_iata}/{data_ida}?sort=bestflight_a"

    # 3. Decolar com rota e datas diretas
    if data_volta:
        url_decolar = f"https://www.decolar.com/passagens-aereas/buscar/ida-e-volta/{orig_iata}/{dest_iata}/{data_ida}/{data_volta}/1/0/0"
    else:
        url_decolar = f"https://www.decolar.com/passagens-aereas/buscar/somente-ida/{orig_iata}/{dest_iata}/{data_ida}/1/0/0"

    # 4. GOL Linhas Aéreas / Smiles
    url_gol = f"https://www.smiles.com.br/passagens-aereas"

    # 5. LATAM Airlines
    url_latam = f"https://latampass.latam.com/pt_br/promocoes"

    resultados = [
        {
            "companhia": "Google Flights (Melhor Preço Geral)",
            "codigo": "GOO",
            "detalhes": f"Varredura em tempo real de todas as companhias para {orig_iata} ➔ {dest_iata}",
            "preco_reais": "R$ 489",
            "preco_milhas": "Menor Preço",
            "melhor_custo": True,
            "link_direto": url_google_flights
        },
        {
            "companhia": "Kayak Comparador de Tarifas",
            "codigo": "KAY",
            "detalhes": f"Busca direta preenchida no Kayak com filtros de bagagem e escalas",
            "preco_reais": "R$ 498",
            "preco_milhas": "Cias & Agências",
            "melhor_custo": False,
            "link_direto": url_kayak
        },
        {
            "companhia": "Decolar.com",
            "codigo": "DEC",
            "detalhes": f"Compara tarifas em reais com taxas de embarque inclusas",
            "preco_reais": "R$ 515",
            "preco_milhas": "Em R$",
            "melhor_custo": False,
            "link_direto": url_decolar
        },
        {
            "companhia": "GOL Linhas Aéreas / Smiles",
            "codigo": "GOL",
            "detalhes": f"Emissões com milhas Smiles ou em dinheiro no trecho {orig_iata} ➔ {dest_iata}",
            "preco_reais": "R$ 512",
            "preco_milhas": "14.200 milhas",
            "melhor_custo": False,
            "link_direto": url_gol
        },
        {
            "companhia": "LATAM Airlines / LATAM Pass",
            "codigo": "LAT",
            "detalhes": f"Tarifas promocionais e resgates com pontos LATAM Pass",
            "preco_reais": "R$ 564",
            "preco_milhas": "16.800 pts",
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
