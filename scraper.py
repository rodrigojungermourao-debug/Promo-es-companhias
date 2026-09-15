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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    termos_busca = [
        "milhas", "pontos", "milheiro", "livelo", "esfera", "smiles", 
        "latam", "latam pass", "azul", "tudoazul", "gol", "tap",
        "passagens", "passagem", "voos", "voo", "aéreo", "aerea",
        "cartão", "cartao", "bônus", "bonus", "transferência", "transferencia"
    ]

    total_novas = 0

    for url in urls:
        try:
            print(f"[SCRAPER] Lendo feed: {url}")
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                feed = feedparser.parse(resp.content)
            else:
                feed = feedparser.parse(url)

            print(f"[SCRAPER] Itens encontrados em {url}: {len(feed.entries)}")

            for entry in feed.entries:
                titulo = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                descricao = entry.get("summary", "").strip()
                data_publicacao = entry.get("published", "")

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

                # Evita duplicidade
                existe = db.query(Promocao).filter(Promocao.link == link).first()
                if not existe:
                    imagem = None
                    if "media_content" in entry and len(entry.media_content) > 0:
                        imagem = entry.media_content[0].get("url")
                    elif "links" in entry:
                        for l in entry.links:
                            if "image" in l.get("type", ""):
                                imagem = l.get("href")
                                break

                    # Cria o objeto sem campos inexistentes no modelo
                    nova = Promocao(
                        titulo=titulo,
                        link=link,
                        data_publicacao=data_publicacao,
                        programa=programa,
                        imagem=imagem
                    )
                    db.add(nova)
                    db.commit()
                    total_novas += 1

        except Exception as e:
            print(f"[SCRAPER ERROR] Falha ao processar {url}: {e}")
            continue

    print(f"[SCRAPER] Total de novas promoções inseridas com sucesso: {total_novas}")
    db.close()
    