import re
import time
from datetime import datetime, timedelta
import feedparser
import requests
from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError
from database import SessionLocal, Promocao

# ==========================================
# CREDENCIAIS DO TELEGRAM
# ==========================================
TELEGRAM_TOKEN = "8946417053:AAHxzBiHG6glT6b8he23gjNgdasKmFY2EVA"
TELEGRAM_CHAT_ID = "8655754996"

IMAGENS_PADRAO = {
    "Livelo": "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=600&auto=format&fit=crop&q=80",
    "Smiles": "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=600&auto=format&fit=crop&q=80",
    "LATAM Pass": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=600&auto=format&fit=crop&q=80",
    "Azul": "https://images.unsplash.com/photo-1508873696983-2df5703bc375?w=600&auto=format&fit=crop&q=80",
    "Esfera": "https://images.unsplash.com/photo-1563013544-824ae1b704d3?w=600&auto=format&fit=crop&q=80",
    "Premmia": "https://images.unsplash.com/photo-1527018607636-06b29f074a3f?w=600&auto=format&fit=crop&q=80",
    "Geral": "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=600&auto=format&fit=crop&q=80"
}

def enviar_card_com_foto(titulo, link, programa=None, imagem=None, eh_alerta=False):
    """Envia uma promoção como um card individual com foto em destaque."""
    if not TELEGRAM_TOKEN or "SEU_TOKEN" in TELEGRAM_TOKEN:
        return

    if eh_alerta:
        cabecalho = "🚨 <b>ALERTA DE PASSAGEM / TARIFA!</b> ✈️\n\n"
    else:
        cabecalho = f"📌 <b>{programa or 'Promoção'}:</b>\n"

    texto = (
        f"{cabecalho}"
        f"<b>{titulo}</b>\n\n"
        f"🔗 {link}"
    )

    url_img = imagem or IMAGENS_PADRAO.get(programa, IMAGENS_PADRAO["Geral"])

    try:
        if url_img and url_img.startswith("http"):
            url_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "photo": url_img,
                "caption": texto,
                "parse_mode": "HTML"
            }
            resp = requests.post(url_api, data=payload, timeout=10)
            if resp.status_code == 200:
                return

        # Fallback para mensagem de texto caso a imagem falhe
        url_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": texto,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        requests.post(url_api, data=payload, timeout=10)
    except Exception as e:
        print(f"[TELEGRAM ERRO]: {e}")

def enviar_alerta_telegram(titulo, link, preco_destaque=None, imagem=None):
    """Dispara o alerta imediato quando surge oportunidade imperdível."""
    enviar_card_com_foto(titulo, link, imagem=imagem, eh_alerta=True)

def enviar_resumo_diario_telegram():
    """Envia individualmente com foto todas as novidades das últimas 24 horas."""
    coletar_promocoes()

    db = SessionLocal()
    limite = datetime.utcnow() - timedelta(hours=24)
    novas = (
        db.query(Promocao)
        .filter((Promocao.data_criacao >= limite) | (Promocao.data_criacao.is_(None)))
        .order_by(Promocao.id.desc())
        .all()
    )
    db.close()

    if not novas:
        return

    # Mensagem de abertura matinal
    try:
        url_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url_api, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"☀️ <b>BOM DIA! RADAR DE MILHAS E PROMOÇÕES</b> ✈️\n\nConfira abaixo as <b>{len(novas)}</b> novidades encontradas nas últimas 24h:",
            "parse_mode": "HTML"
        }, timeout=10)
    except Exception:
        pass

    # Dispara cada promoção com foto
    for item in novas:
        enviar_card_com_foto(
            titulo=item.titulo,
            link=item.link,
            programa=item.programa,
            imagem=item.imagem,
            eh_alerta=False
        )
        time.sleep(0.8)  # Pequeno intervalo para respeitar o limite de taxa do Telegram

def enviar_todas_promocoes_hoje():
    """Dispara individualmente com foto todas as ofertas cadastradas no banco."""
    coletar_promocoes()

    db = SessionLocal()
    todas = db.query(Promocao).order_by(Promocao.id.desc()).all()
    db.close()

    if not todas:
        return

    for item in todas:
        enviar_card_com_foto(
            titulo=item.titulo,
            link=item.link,
            programa=item.programa,
            imagem=item.imagem,
            eh_alerta=False
        )
        time.sleep(0.8)

def avaliar_oferta(titulo):
    t = titulo.lower()
    vale = False
    preco_str = None

    gatilhos = [
        "menor preço", "histórico", "imperdível", "muito barato", 
        "erro", "bug", "alerta", "barato de verdade", "super desconto", "relâmpago", "relampago"
    ]
    if any(g in t for g in gatilhos):
        vale = True

    match_reais = re.search(r'r\$\s?(\d+[\.,]?\d*)', t)
    if match_reais:
        raw_val = match_reais.group(1).replace('.', '').replace(',', '.')
        try:
            valor = float(raw_val)
            preco_str = f"R$ {int(valor)}"
            if valor <= 499:
                vale = True
            elif valor <= 1499 and any(x in t for x in ["buenos aires", "santiago", "orlando", "miami", "chile", "eua", "europa"]):
                vale = True
        except ValueError:
            pass

    match_milhas = re.search(r'(\d+)\s?(mil|milhas|pontos)', t)
    if match_milhas:
        try:
            qtd = int(match_milhas.group(1))
            preco_str = f"{qtd}k pts"
            if qtd <= 12:
                vale = True
        except ValueError:
            pass

    palavras_passagem = ["passag", "voo", "aéreo", "aereo", "tarifa", "trecho", "ida e volta"]
    eh_passagem = any(p in t for p in palavras_passagem)

    return (vale and eh_passagem), preco_str

def extrair_imagem(entry, headers, programa):
    if "media_content" in entry and len(entry.media_content) > 0:
        url = entry.media_content[0].get("url")
        if url:
            return url
            
    if "links" in entry:
        for l in entry.links:
            if "image" in l.get("type", ""):
                return l.get("href")

    conteudo_html = ""
    if "content" in entry and len(entry.content) > 0:
        conteudo_html = entry.content[0].value
    elif "summary" in entry:
        conteudo_html = entry.summary

    if conteudo_html:
        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', conteudo_html)
        if img_match:
            img_url = img_match.group(1)
            if not any(x in img_url.lower() for x in ["feedburner", "1x1", "pixel", "gravatar"]):
                return img_url

    try:
        link = entry.get("link", "")
        if link:
            resp = requests.get(link, headers=headers, timeout=3)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                meta = soup.find("meta", property="og:image")
                if meta and meta.get("content"):
                    return meta["content"]
    except Exception:
        pass

    return IMAGENS_PADRAO.get(programa, IMAGENS_PADRAO["Geral"])

def coletar_promocoes():
    db = SessionLocal()

    urls = [
        "https://www.melhoresdestinos.com.br/feed",
        "https://passageirodeprimeira.com/feed/?post_type=post",
        "https://www.passagensimperdiveis.com.br/feed/",
        "https://www.melhorescartoes.com.br/feed",
        "https://pontospravoar.com/feed/",
        "https://mestredasmilhas.com.br/feed/"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=8)
            feed = feedparser.parse(resp.content if resp.status_code == 200 else url)

            for entry in feed.entries:
                titulo = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                descricao = entry.get("summary", "").strip()

                if not titulo or not link:
                    continue

                texto = f"{titulo} {descricao}".lower()

                if "premmia" in texto:
                    if not any(t in texto for t in ["smiles", "azul", "milhas", "pontos", "bônus", "bonus", "transferência"]):
                        continue
                    programa = "Premmia"
                elif "livelo" in texto:
                    programa = "Livelo"
                elif "esfera" in texto:
                    programa = "Esfera"
                elif "smiles" in texto:
                    programa = "Smiles"
                elif "latam" in texto:
                    programa = "LATAM Pass"
                elif "azul" in texto or "tudoazul" in texto:
                    programa = "Azul"
                else:
                    programa = "Geral"

                vale_a_pena, preco_destaque = avaliar_oferta(titulo)
                promo = db.query(Promocao).filter(Promocao.link == link).first()

                if not promo:
                    imagem = extrair_imagem(entry, headers, programa)
                    nova = Promocao(
                        titulo=titulo,
                        link=link,
                        programa=programa,
                        imagem=imagem,
                        vale_a_pena=vale_a_pena,
                        preco_destaque=preco_destaque,
                        data_criacao=datetime.utcnow()
                    )
                    try:
                        db.add(nova)
                        db.commit()

                        if vale_a_pena:
                            enviar_alerta_telegram(titulo, link, preco_destaque, imagem)

                    except IntegrityError:
                        db.rollback()
                    except Exception:
                        db.rollback()

        except Exception as e:
            print(f"[SCRAPER ERROR] {url}: {e}")
            continue

    db.close()
    
