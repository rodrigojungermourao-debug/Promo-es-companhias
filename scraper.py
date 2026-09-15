import feedparser
import requests
from database import SessionLocal, Promocao

def coletar_promocoes():
    db = SessionLocal()
    
    # Feeds RSS de milhas
    urls = [
        "https://www.melhoresdestinos.com.br/feed",
        "https://passageirodeprimeira.com/feed/?post_type=post"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    total_novas = 0

    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            feed = feedparser.parse(resp.content)

            for entry in feed.entries:
                titulo = getattr(entry, "title", "").strip()
                link = getattr(entry, "link", "").strip()
                if not titulo or not link:
                    continue

                titulo_lower = titulo.lower()

                programas = []
                if "livelo" in titulo_lower:
                    programas.append("Livelo")
                if "smiles" in titulo_lower:
                    programas.append("Smiles")
                if "esfera" in titulo_lower:
                    programas.append("Esfera")
                if "azul" in titulo_lower or "tudoazul" in titulo_lower:
                    programas.append("Azul")
                if "latam" in titulo_lower:
                    programas.append("LATAM Pass")

                # Se encontrou um programa específico
                if programas:
                    programa_str = " / ".join(programas)
                # Se não tem o nome do programa, mas fala de milhas/pontos/bônus/cartão
                elif any(termo in titulo_lower for termo in ["milhas", "pontos", "bônus", "transferência", "cartão", "cashback"]):
                    programa_str = "Geral"
                else:
                    # Se não for de milhas/pontos, pula o artigo (ex: promoção só de passagem sem milhas)
                    continue

                existe = db.query(Promocao).filter_by(titulo=titulo).first()
                if not existe:
                    nova_promo = Promocao(titulo=titulo, link=link, programa=programa_str)
                    db.add(nova_promo)
                    total_novas += 1

            db.commit()
        except Exception as e:
            print(f"Erro ao ler feed {url}: {e}")

    print(f"Coleta concluída! {total_novas} novas promoções salvas no banco.")
    db.close()

if __name__ == "__main__":
    coletar_promocoes()
    