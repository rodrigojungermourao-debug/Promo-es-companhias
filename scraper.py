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

    # Termos padrao de milhas e cartoes
    termos_milhas = ["livelo", "smiles", "esfera", "azul", "latam pass", "latam", "pontos", "milhas", "milheiro"]
    termos_premmia_bonus = ["smiles", "azul", "milhas", "pontos", "bônus", "bonus", "transferência", "transferencia"]

    for url in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                titulo = entry.get("title", "")
                link = entry.get("link", "")
                descricao = entry.get("summary", "")
                data_publicacao = entry.get("published", "")

                texto_completo = f"{titulo} {descricao}".lower()

                # Regra padrao de milhas
                relevante_geral = any(t in texto_completo for t in termos_milhas)

                # Regra do Premmia: apenas se envolver milhas/transferencia
                relevante_premmia = "premmia" in texto_completo and any(t in texto_completo for t in termos_premmia_bonus)

                if relevante_geral or relevante_premmia:
                    # Identifica a tag do programa
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

                    # Salva no banco evitando duplicatas
                    existe = db.query(Promocao).filter(Promocao.link == link).first()
                    if not existe:
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