import re
import feedparser
import requests
from bs4 import BeautifulSoup
from database import SessionLocal, Promocao

IMAGENS_PADRAO = {
    "Livelo": "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=600&auto=format&fit=crop&q=80",
    "Smiles": "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=600&auto=format&fit=crop&q=80",
    "LATAM Pass": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=600&auto=format&fit=crop&q=80",
    "Azul": "https://images.unsplash.com/photo-1508873696983-2df5703bc375?w=600&auto=format&fit=crop&q=80",
    "Esfera": "https://images.unsplash.com/photo-1563013544-824ae1b704d3?w=600&auto=format&fit=crop&q=80",
    "Premmia": "https://images.unsplash.com/photo-1527018607636-06b29f074a3f?w=600&auto=format&fit=crop&q=80",
    "Geral": "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=600&auto=format&fit=crop&q=80"
}

def extrair_imagem(entry, headers, programa):
    # 1. media_content ou links do feed
    if "media_content" in entry and len(entry.media_content) > 0:
        url = entry.media_content[0].get("url")
        if url:
            return url
            
    if "links" in entry:
        for l in entry.links:
            if "image" in l.get("type", ""):
                return l.get("href")

    # 2. Tag <img> dentro do conteúdo HTML da postagem
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

    # 3. Metatag og:image na página original
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

    # 4. Fallback temático: nunca deixa o card em branco
    return IMAGENS_PADRAO.get(programa, IMAGENS_PADRAO["Geral"])


def coletar_promocoes():
    db = SessionLocal()

    urls = [
        "https://www.melhoresdestinos.com.br/feed",
        "https://passageirodeprimeira.com/feed/?post_type=post",
        "https://www.melhorescartoes.com.br/feed",
        "https://pontospravoar.com/feed/",
        "https://mestredasmilhas.com.br/feed/"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    termos_busca = [
        "milhas", "pontos", "milheiro", "livelo", "esfera", "smiles", 
        "latam", "latam pass", "azul", "tudoazul", "gol", "tap",
        "passagens", "passagem", "voos", "voo", "aéreo", "aerea",
        "cartão", "cartao", "bônus", "bonus", "transferência", "transferencia"
    ]

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

                promo = db.query(Promocao).filter(Promocao.link == link).first()

                if not promo:
                    imagem = extrair_imagem(entry, headers, programa)
                    nova = Promocao(
                        titulo=titulo,
                        link=link,
                        programa=programa,
                        imagem=imagem
                    )
                    db.add(nova)
                    db.commit()
                elif not promo.imagem:
                    promo.imagem = extrair_imagem(entry, headers, programa)
                    db.commit()

        except Exception as e:
            print(f"[SCRAPER ERROR] {url}: {e}")
            continue

    db.close()
    