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
        context={"buscou": False}
    )

@app.get("/passagens/buscar")
def buscar_voos(request: Request, origem: str, destino: str, data_ida: str, data_volta: str = None):
    # Links diretos estruturados para consulta imediata nas companhias e Google Flights
    gf_url = f"https://www.google.com/travel/flights?q=Voos%20de%20{origem}%20para%20{destino}%20em%20{data_ida}"
    gol_url = "https://www.voegol.com.br"
    latam_url = "https://www.latamairlines.com/br/pt"
    azul_url = "https://www.voeazul.com.br"

    resultados = [
        {
            "companhia": "Google Flights / Menor Tarifa",
            "detalhes": f"Varredura consolidada de todas as empresas no trecho {origem} ➔ {destino}",
            "preco": "Tarifas em tempo real",
            "vale_a_pena": True,
            "link_direto": gf_url
        },
        {
            "companhia": "GOL Linhas Aéreas / Smiles",
            "detalhes": f"Voo direto ou conexão com emissão em R$ ou Milhas Smiles",
            "preco": "Consultar trecho",
            "vale_a_pena": False,
            "link_direto": gol_url
        },
        {
            "companhia": "LATAM Airlines / LATAM Pass",
            "detalhes": f"Tarifas promocionais e resgate com pontos LATAM Pass",
            "preco": "Consultar trecho",
            "vale_a_pena": False,
            "link_direto": latam_url
        },
        {
            "companhia": "Azul Linhas Aéreas",
            "detalhes": f"Voos nacionais e conexões internacionais",
            "preco": "Consultar trecho",
            "vale_a_pena": False,
            "link_direto": azul_url
        }
    ]

    return templates.TemplateResponse(
        request=request,
        name="passagens.html",
        context={
            "buscou": True,
            "origem": origem,
            "destino": destino,
            "data_ida": data_ida,
            "data_volta": data_volta,
            "resultados": resultados
        }
    )

@app.get("/atualizar")
def atualizar(background_tasks: BackgroundTasks):
    background_tasks.add_task(scraper.coletar_promocoes)
    return RedirectResponse(url="/", status_code=303)
