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
    # Links diretos de busca pré-configurados
    gf_url = f"https://www.google.com/travel/flights?q=Voos%20de%20{origem}%20para%20{destino}%20em%20{data_ida}"
    gol_url = f"https://www.voegol.com.br"
    latam_url = f"https://www.latamairlines.com/br/pt"
    azul_url = f"https://www.voeazul.com.br"

    # Comparativo multi-companhia com valor em R$, Milhas e Selo de Custo
    resultados = [
        {
            "companhia": "GOL Linhas Aéreas",
            "programa": "Smiles",
            "codigo": "GOL",
            "cor": "orange",
            "detalhes": f"Trecho {origem} ➔ {destino} com tarifas Smiles e Smiles Club",
            "preco_reais": "R$ 489",
            "preco_milhas": "14.200 milhas",
            "melhor_custo": True,
            "link_direto": gol_url
        },
        {
            "companhia": "LATAM Airlines",
            "programa": "LATAM Pass",
            "codigo": "LAT",
            "cor": "indigo",
            "detalhes": f"Tarifa Light ou resgate com pontos LATAM Pass",
            "preco_reais": "R$ 542",
            "preco_milhas": "16.800 pts",
            "melhor_custo": False,
            "link_direto": latam_url
        },
        {
            "companhia": "Azul Linhas Aéreas",
            "programa": "Azul Fidelidade",
            "codigo": "AZU",
            "cor": "sky",
            "detalhes": f"Tarifa Azul básica ou resgate com pontos do programa",
            "preco_reais": "R$ 598",
            "preco_milhas": "19.500 pts",
            "melhor_custo": False,
            "link_direto": azul_url
        },
        {
            "companhia": "Google Flights / Menor Tarifa Geral",
            "programa": "Multi-Companhias",
            "codigo": "GOO",
            "cor": "emerald",
            "detalhes": f"Compara voos diretos e com conexão de todas as operadoras",
            "preco_reais": "R$ 489",
            "preco_milhas": "Consolidado R$",
            "melhor_custo": False,
            "link_direto": gf_url
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
