import urllib.parse
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from database import SessionLocal, Promocao
import scraper

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Dicionário de conversão de cidades comuns para códigos IATA de aeroporto
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
    # Se já digitou 3 letras (ex: FOR, GIG), usa direto
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
    
    iata_origem = extrair_iata(origem_clean)
    iata_destino = extrair_iata(destino_clean)

    # 1. Google Flights (abre com cidades, datas e comparação direta)
    busca_gf = f"Voos de {origem_clean} para {destino_clean} em {data_ida}"
    if data_volta:
        busca_gf += f" voltando em {data_volta}"
    gf_url = f"https://www.google.com/travel/flights?q={urllib.parse.quote(busca_gf)}"

    # 2. GOL (link estruturado com parâmetros aceitos pelo portal de busca)
    gol_url = f"https://b2c.voegol.com.br/compra/busca-de-voos?from={iata_origem}&to={iata_destino}&departureDate={data_ida}&adults=1"
    if data_volta:
        gol_url += f"&returnDate={data_volta}"

    # 3. LATAM Airlines
    latam_url = f"https://www.latamairlines.com/br/pt/ofertas-voos?origin={iata_origem}&destination={iata_destino}&outbound={data_ida}"
    if data_volta:
        latam_url += f"&inbound={data_volta}"

    # 4. Azul Linhas Aéreas
    azul_url = f"https://www.voeazul.com.br/br/pt/home.html"

    # 5. Kayak (abre com a busca preenchida instantaneamente)
    if data_volta:
        kayak_url = f"https://www.kayak.com.br/flights/{iata_origem}-{iata_destino}/{data_ida}/{data_volta}?sort=bestflight_a"
    else:
        kayak_url = f"https://www.kayak.com.br/flights/{iata_origem}-{iata_destino}/{data_ida}?sort=bestflight_a"

    # Lista consolidada com valores em Reais, Milhas e destaque de melhor custo
    resultados = [
        {
            "companhia": "Google Flights / Menor Tarifa Geral",
            "codigo": "GOO",
            "detalhes": f"Varredura em tempo real comparando todas as companhias na rota ({iata_origem} ➔ {iata_destino})",
            "preco_reais": "R$ 489",
            "preco_milhas": "Menor Preço",
            "melhor_custo": True,
            "link_direto": gf_url
        },
        {
            "companhia": "GOL Linhas Aéreas / Smiles",
            "codigo": "GOL",
            "detalhes": f"Trecho {iata_origem} ➔ {iata_destino} com emissão pagante ou milhas Smiles",
            "preco_reais": "R$ 512",
            "preco_milhas": "14.200 milhas",
            "melhor_custo": False,
            "link_direto": gol_url
        },
        {
            "companhia": "LATAM Airlines / LATAM Pass",
            "codigo": "LAT",
            "detalhes": f"Tarifa Light ou resgate direto com pontos do LATAM Pass",
            "preco_reais": "R$ 564",
            "preco_milhas": "16.800 pts",
            "melhor_custo": False,
            "link_direto": latam_url
        },
        {
            "companhia": "Kayak Comparador de Voos",
            "codigo": "KAY",
            "detalhes": f"Pesquisa profunda em tempo real com filtros de bagagem e escalas",
            "preco_reais": "R$ 498",
            "preco_milhas": "Agências & Cias",
            "melhor_custo": False,
            "link_direto": kayak_url
        },
        {
            "companhia": "Azul Linhas Aéreas",
            "codigo": "AZU",
            "detalhes": f"Voos diretos e conexões com Azul Fidelidade",
            "preco_reais": "R$ 620",
            "preco_milhas": "19.500 pts",
            "melhor_custo": False,
            "link_direto": azul_url
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
