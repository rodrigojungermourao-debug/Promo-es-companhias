import feedparser
import requests
from bs4 import BeautifulSoup
from database import SessionLocal, Promocao

def extrair_imagem_real(url, headers):
    try:
        resp = requests.get(url, headers=headers, timeout=4)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            meta_img = soup.find("meta", property="og:image")
            if meta_img and meta_img.get("content"):
                return meta_img["content"]
            
            wp_img = soup.find("img", class_="wp-post-image")
            if wp_img and wp_img.get("src"):
                return wp_img["src"]
    except Exception:
        pass
    return None

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

    termos_milhas = ["livelo", "smiles", "esfera", "azul", "latam pass", "latam", "pontos", "milhas", "milheiro"]
    termos_premmia_bonus = ["smiles", "azul", "milhas", "pontos", "bônus", "bonus", "transferência", "transferencia"]

    for url in urls:
        try:
            # Baixa com requests usando headers do Chrome para nao ser bloqueado
            response = requests.get(url, headers=headers, timeout=6)
            if response.status_code != 200:
                continue
            
            feed = feedparser.parse(response.content)
            
            for entry in feed.entries:
                titulo = entry.get("title", "")
                link = entry.get("link", "")
                descricao = entry.get("summary", "")
                data_publicacao = entry.get("published", "")

                texto_completo = f"{titulo} {descricao}".lower()

                relevante_geral = any(t in texto_completo for t in termos_milhas)
                relevante_premmia = "premmia" in texto_completo and any(t in texto_completo for t in termos_premmia_bonus)

                if relevante_geral or relevante_premmia:
                    if "premmia" in texto_completo:
                        programa = "Premmia"
                    elif "livelo" in texto_completo:
                        programa = "Livelo"
                    elif "esfera" in texto_completo:
                        programa = "Esfera"
                    elif "smiles" in texto_completo:
                        programa = "Smiles"
                    elif "latam" in texto_completo:
                        programa = "LATAM Pass"
                    elif "azul" in texto_completo:
                        programa = "Azul"
                    else:
                        programa = "Geral"

                    existe = db.query(Promocao).filter(Promocao.link == link).first()
                    if not existe:
                        # Tenta extrair imagem em tags do feed primeiro
                        imagem_capa = None
                        if "media_content" in entry and len(entry.media_content) > 0:
                            imagem_capa = entry.media_content[0].get("url")
                        elif "links" in entry:
                            for l in entry.links:
                                if "image" in l.get("type", ""):
                                    imagem_capa = l.get("href")
                                    break
                        
                        # Se nao achou no feed, busca na pagina
                        if not imagem_capa:
                            imagem_capa = extrair_imagem_real(link, headers)

                        nova = Promocao(
                            titulo=titulo,
                            link=link,
                            descricao=descricao,
                            data_publicacao=data_publicacao,
                            programa=programa,
                            imagem=imagem_capa
                        )
                        db.add(nova)
                        db.commit()
        except Exception:
            continue

    db.close()
    