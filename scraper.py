import feedparser
import requests
from database import SessionLocal, Promocao

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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    termos_milhas = ["livelo", "smiles", "esfera", "azul", "latam pass", "latam", "pontos", "milhas", "milheiro", "tudoazul"]
    termos_premmia_bonus = ["smiles", "azul", "milhas", "pontos", "bônus", "bonus", "transferência", "transferencia"]

    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                feed = feedparser.parse(resp.content)
            else:
                feed = feedparser.parse(url)

            for entry in feed.entries:
                titulo = entry.get("title", "")
                link = entry.get("link", "")
                descricao = entry.get("summary", "")
                data_publicacao = entry.get("published", "")

                texto = f"{titulo} {descricao}".lower()

                relevante_geral = any(t in texto for t in termos_milhas)
                relevante_premmia = "premmia" in texto and any(t in texto for t in termos_premmia_bonus)

                if relevante_geral or relevante_premmia:
                    if "premmia" in texto:
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

                    existe = db.query(Promocao).filter(Promocao.link == link).first()
                    if not existe:
                        # Extrai imagem diretamente do feed (rápido e sem requisição extra)
                        imagem = None
                        if "media_content" in entry and len(entry.media_content) > 0:
                            imagem = entry.media_content[0].get("url")
                        elif "links" in entry:
                            for l in entry.links:
                                if "image" in l.get("type", ""):
                                    imagem = l.get("href")
                                    break

                        nova = Promocao(
                            titulo=titulo,
                            link=link,
                            descricao=descricao,
                            data_publicacao=data_publicacao,
                            programa=programa,
                            imagem=imagem
                        )
                        db.add(nova)
                        db.commit()
        except Exception:
            continue

    db.close()
    