import urllib.parse
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
    # Codificação dos textos para parâmetros válidos de URL
    origem_clean = origem.strip()
    destino_clean = destino.strip()
    
    # 1. Google Flights (carrega com rota, data de ida e volta exatas)
    termo_busca = f"Voos de {origem_clean} para {destino_clean} em {data_ida}"
    if data_volta:
        termo_busca += f" voltando em {data_volta}"
    gf_url = f"https://www.google.com/travel/flights?q={urllib.parse.quote(termo_busca)}"

    # 2. Skyscanner (busca profunda multi-companhia consolidada)
    sky_url = f"https://www.skyscanner.com.br/transporte/passagens-aereas/{urllib.parse.quote(origem_clean)}/{urllib.parse.quote(destino_clean)}/{data_ida}/"
    if data_volta:
        sky_url += f"{data_volta}/"

    # 3. GOL / Smiles (link direto para busca oficial)
    gol_url = f"https://b2c.voegol.com.br/compra/busca-de-voos?from={urllib.parse.quote(origem_clean)}&to={urllib.parse.quote(destino_clean)}&departureDate={data_ida}&adults=1"

    # 4. LATAM Airlines
    latam_url = f"https://www.latamairlines.com/br/pt/ofertas-voos?origin={urllib.parse.quote(origem_clean)}&destination={urllib.parse.quote(destino_clean)}"

    # 5. Azul Linhas Aéreas
    azul_url = f"https://www.voeazul.com.br/br/pt/home.html?origem={urllib.parse.quote(origem_clean)}&destino={urllib.parse.quote(destino_clean)}&ida={data_ida}"

    resultados = [
        {
            "companhia": "Google Flights / Menor Tarifa Geral",
            "programa": "Todas as Companhias",
            "codigo": "GOO",
            "detalhes": f"Varredura em tempo real com todos os voos de {origem_clean} para {destino_clean}",
            "preco_reais": "Melhor Preço",
            "preco_milhas": "Consolidado R$",
            "melhor_custo": True,
            "link_direto": gf_url
        },
        {
            "companhia": "GOL Linhas Aéreas / Smiles",
            "programa": "Smiles",
            "codigo": "GOL",
            "detalhes": f"Ver voos disponíveis e resgate no trecho {origem_clean} ➔ {destino_clean}",
            "preco_reais": "Consultar Trecho",
            "preco_milhas": "Tabela Smiles",
            "melhor_custo": False,
            "link_direto": gol_url
        },
        {
            "companhia": "LATAM Airlines / LATAM Pass",
            "programa": "LATAM Pass",
            "codigo": "LAT",
            "detalhes": f"Ver opções oficiais de voo para {destino_clean}",
            "preco_reais": "Consultar Trecho",
            "preco_milhas": "Tabela LATAM",
            "melhor_custo": False,
            "link_direto": latam_url
        },
        {
            "companhia": "Azul Linhas Aéreas",
            "programa": "Azul Fidelidade",
            "codigo": "AZU",
            "detalhes": f"Ver disponibilidade oficial da Azul na rota",
            "preco_reais": "Consultar Trecho",
            "preco_milhas": "Tabela Azul",
            "melhor_custo": False,
            "link_direto": azul_url
        },
        {
            "companhia": "Skyscanner Comparador",
            "programa": "Agregador Global",
            "codigo": "SKY",
            "detalhes": f"Comparativo de companhias low-cost e agências de viagem",
            "preco_reais": "Consultar Trecho",
            "preco_milhas": "Em R$",
            "melhor_custo": False,
            "link_direto": sky_url
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
