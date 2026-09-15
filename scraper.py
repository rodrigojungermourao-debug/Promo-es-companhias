import feedparser
import requests
from bs4 import BeautifulSoup
from database import SessionLocal, Promocao

def extrair_imagem_real(url, headers):
    """Acessa a pagina da materia e pega a imagem oficial da capa (og:image)"""
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            
            # 1. Tenta a imagem principal de compartilhamento (Open Graph)
            og_img = soup.find("meta", property="og:image")
            if og_img and og_img.get("content"):
                return og_img["content"]
            
            # 2. Tenta meta twitter:image
            tw_img = soup.find("meta", attrs={"name": "twitter:image"})
            if tw_img and tw_img.get("content"):
                return tw_img["content"]
                
            # 3. Tenta imagem de destaque comum do WordPress
            wp_img = soup.find("img", class_="wp-post-image")
            if wp_img and wp_img.get("src"):
                return wp_img["src"]
    except Exception:
        pass
    return None

def coletar_promocoes():
    db = SessionLocal()

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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    # Atualiza as promocoes que ja estao salvas no banco mas ainda estao sem imagem
    sem_foto = db.query(Promocao).filter((Promocao.imagem == None) | (Promocao.imagem == "")).all()
    for promo in sem_foto:
        img = extrair_imagem_real(promo.link, headers)
        if img:
            promo.imagem = img
    db.commit()

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

                if programas:
                    programa_str = " / ".join(programas)
                elif any(termo in titulo_lower for termo in ["milhas", "pontos", "bônus", "transferência", "cartão", "cashback"]):
                    programa_str = "Geral"
                else:
                    continue

                existe = db.query(Promocao).filter_by(titulo=titulo).first()
                if not existe:
                    # Busca a imagem oficial da pagina
                    imagem_url = extrair_imagem_real(link, headers)
                    nova_promo = Promocao(titulo=titulo, link=link, programa=programa_str, imagem=imagem_url)
                    db.add(nova_promo)
                    total_novas += 1
                elif not existe.imagem:
                    existe.imagem = extrair_imagem_real(link, headers)

            db.commit()
        except Exception as e:
            print(f"Erro ao ler feed {url}: {e}")

    print(f"Coleta concluída! {total_novas} novas promoções salvas.")
    db.close()

if __name__ == "__main__":
    coletar_promocoes()
    