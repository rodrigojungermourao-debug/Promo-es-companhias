import re
from database import Promocao, SessionLocal
import feedparser
import requests


def extrair_imagem(entry):
  # 1. Tenta media_content
  if hasattr(entry, "media_content") and entry.media_content:
    return entry.media_content[0].get("url")

  # 2. Tenta enclosure
  if hasattr(entry, "enclosures") and entry.enclosures:
    return entry.enclosures[0].get("href")

  # 3. Tenta pegar a primeira tag <img> do resumo ou conteúdo
  corpo = getattr(entry, "summary", "") or getattr(entry, "description", "")
  match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', corpo)
  if match:
    return match.group(1)

  return None


def coletar_promocoes():
  db = SessionLocal()

  urls = [
      "https://www.melhoresdestinos.com.br/feed",
      "https://passageirodeprimeira.com/feed/?post_type=post",
  ]

  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/122.0.0.0 Safari/537.36"
      )
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

        if programas:
          programa_str = " / ".join(programas)
        elif any(
            termo in titulo_lower
            for termo in [
                "milhas",
                "pontos",
                "bônus",
                "transferência",
                "cartão",
                "cashback",
            ]
        ):
          programa_str = "Geral"
        else:
          continue

        imagem_url = extrair_imagem(entry)

        existe = db.query(Promocao).filter_by(titulo=titulo).first()
        if not existe:
          nova_promo = Promocao(
              titulo=titulo, link=link, programa=programa_str, imagem=imagem_url
          )
          db.add(nova_promo)
          total_novas += 1
        elif not existe.imagem and imagem_url:
          existe.imagem = imagem_url

      db.commit()
    except Exception as e:
      print(f"Erro ao ler feed {url}: {e}")

  print(f"Coleta concluída! {total_novas} novas promoções salvas.")
  db.close()


if __name__ == "__main__":
  coletar_promocoes()
  