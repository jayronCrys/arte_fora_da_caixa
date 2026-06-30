import re
import json

TAG_PATTERN = re.compile(r'\[#(\w+)#\]')

def parse_html_to_content_list(html: str) -> list:
    """
    Retorna lista de objetos no formato final:
    [
      {"tipo": "markdown", "html": "..."},
      {"tipo": "exemplo", "conteudo": "texto ou dict"},
      {"tipo": "exercicio", "conteudo": {"pergunta":..., ...}},
      {"tipo": "quebra_pagina"}
    ]
    """
    # 1. Encontrar todas as tags
    matches = list(TAG_PATTERN.finditer(html))
    if not matches:
        # Nenhuma tag especial; tudo é markdown
        return [{"tipo": "markdown", "html": html.strip()}]

    items = []
    last_pos = 0

    # 2. Varrer matches sequencialmente
    i = 0
    while i < len(matches):
        match = matches[i]
        tag_name = match.group(1)
        start = match.start()
        end = match.end()

        # Trecho anterior vira markdown
        if start > last_pos:
            chunk = html[last_pos:start].strip()
            if chunk:
                items.append({"tipo": "markdown", "html": chunk})

        # Tratamento especial para QUEBRA_PAGINA (auto-fechável)
        if tag_name == "QUEBRA_PAGINA":
            items.append({"tipo": "quebra_pagina"})
            last_pos = end
            i += 1
            continue

        # Tag normal: precisa de fechamento
        # Buscar próximo fechamento com mesmo nome
        close_pattern = re.escape(f"[#{tag_name}#]")
        close_match = re.search(close_pattern, html[end:])
        if not close_match:
            # Fechamento não encontrado; trata como auto-fechável ou ignora?
            # Por segurança, tratamos como uma marcação inválida e continuamos
            items.append({"tipo": "markdown", "html": match.group()})
            last_pos = end
            i += 1
            continue

        inner_start = end
        inner_end = end + close_match.start()
        inner_html = html[inner_start:inner_end].strip()

        # Avança o i até depois do fechamento
        # Encontra o índice do match de fechamento na lista de matches
        close_match_start = end + close_match.start()
        # Pula todos os matches que estão antes ou sobre o bloco interno
        while i < len(matches) and matches[i].start() < close_match_start + len(close_match.group()):
            i += 1
        # Agora i aponta para o primeiro match após o fechamento

        # Monta objeto conforme o tipo
        obj = {"tipo": tag_name.lower()}  # normalizado para minúsculas
        if tag_name.upper() == "EXERCICIO":
            # Tenta interpretar inner_html como JSON; senão, mantém string
            try:
                obj["conteudo"] = json.loads(inner_html)
            except json.JSONDecodeError:
                obj["conteudo"] = inner_html
        else:
            # Para EXEMPLO e outras tags não especiais
            obj["conteudo"] = inner_html

        items.append(obj)
        last_pos = close_match_start + len(close_match.group())

    # Resto final após último match
    if last_pos < len(html):
        tail = html[last_pos:].strip()
        if tail:
            items.append({"tipo": "markdown", "html": tail})

    return items