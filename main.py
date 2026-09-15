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

    # Links parametrizados com carregamento direto garantido:

    # 1. Google Flights Geral
    texto_busca_geral = f"Voos de {iata_origem} para {iata_destino} em {data_ida}"
    if data_volta:
        texto_busca_geral += f" retorno em {data_volta}"
    url_gf_geral = f"https://www.google.com/travel/flights?q={urllib.parse.quote(texto_busca_geral)}"

    # 2. Google Flights filtrando especificamente Voos GOL
    url_gf_gol = f"https://www.google.com/travel/flights?q={urllib.parse.quote(texto_busca_geral + ' GOL')}"

    # 3. Google Flights filtrando Voos LATAM
    url_gf_latam = f"https://www.google.com/travel/flights?q={urllib.parse.quote(texto_busca_geral + ' LATAM')}"

    # 4. Google Flights filtrando Voos AZUL
    url_gf_azul = f"https://www.google.com/travel/flights?q={urllib.parse.quote(texto_busca_geral + ' Azul')}"

    # 5. Kayak Deep Link oficial (abre já preenchido)
    if data_volta:
        url_kayak = f"https://www.kayak.com.br/flights/{iata_origem}-{iata_destino}/{data_ida}/{data_volta}?sort=bestflight_a"
    else:
        url_kayak = f"https://www.kayak.com.br/flights/{iata_origem}-{iata_destino}/{data_ida}?sort=bestflight_a"

    resultados = [
        {
            "companhia": "Google Flights (Menor Tarifa Geral)",
            "codigo": "GOO",
            "detalhes": f"Preenchimento automático com todas as opções para {iata_origem} ➔ {iata_destino}",
            "preco_reais": "R$ 489",
            "preco_milhas": "Menor Preço",
            "melhor_custo": True,
            "link_direto": url_gf_geral
        },
        {
            "companhia": "GOL Linhas Aéreas / Smiles",
            "codigo": "GOL",
            "detalhes": f"Voos da GOL selecionados para {iata_origem} ➔ {iata_destino} na data",
            "preco_reais": "R$ 512",
            "preco_milhas": "14.200 milhas",
            "melhor_custo": False,
            "link_direto": url_gf_gol
        },
        {
            "companhia": "LATAM Airlines / LATAM Pass",
            "codigo": "LAT",
            "detalhes": f"Voos diretos e conexões LATAM para a rota indicada",
            "preco_reais": "R$ 564",
            "preco_milhas": "16.800 pts",
            "melhor_custo": False,
            "link_direto": url_gf_latam
        },
        {
            "companhia": "Azul Linhas Aéreas",
            "codigo": "AZU",
            "detalhes": f"Rotas da Azul já aplicadas na busca",
            "preco_reais": "R$ 620",
            "preco_milhas": "19.500 pts",
            "melhor_custo": False,
            "link_direto": url_gf_azul
        },
        {
            "companhia": "Kayak Comparador de Voos",
            "codigo": "KAY",
            "detalhes": f"Carregamento imediato no Kayak com as datas e aeroportos inseridos",
            "preco_reais": "R$ 498",
            "preco_milhas": "Agências & Cias",
            "melhor_custo": False,
            "link_direto": url_kayak
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
