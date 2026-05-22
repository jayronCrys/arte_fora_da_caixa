import re
import json
import mistune  # Pode ser substituído por mistune se preferir

# Regex otimizado para capturar o tipo do bloco e o conteúdo interno multilinhas
BLOCO_PATTERN = re.compile(
    r'(?:^|\n):::(\w[\w-]*)\s*\n(.*?)\n:::\s*(?=\n|$)', 
    re.DOTALL
)

def renderizar_estrutura(texto_bruto):
    resultado = []
    cursor = 0
    
    for match in BLOCO_PATTERN.finditer(texto_bruto):
        # 1. Extrai a prosa que veio ANTES do bloco customizado
        prosa_antes = texto_bruto[cursor:match.start()].strip()
        if prosa_antes:
            # Aqui o conversor entra em ação apenas para o texto normal
            resultado.append({
                "tipo": "markdown",
                "html": mistune.html(prosa_antes)
            })
        
        # 2. Extrai o bloco customizado sem mexer no conteúdo interno
        tipo_bloco = match.group(1)
        conteudo_bloco = match.group(2).strip()
        
        # Se for um bloco de exercício (que espera um JSON interno), podemos fazer o parse automático
        if tipo_bloco == "exercicio":
            try:
                conteudo_bloco = json.loads(conteudo_bloco)
            except json.JSONDecodeError:
                pass # Mantém como string caso o autor erre a sintaxe do JSON
        
        resultado.append({
            "tipo": tipo_bloco,
            "conteudo": conteudo_bloco
        })
        
        cursor = match.end()
        
    # 3. Captura qualquer prosa que tenha sobrado após o último bloco
    prosa_depois = texto_bruto[cursor:].strip()
    if prosa_depois:
        resultado.append({
            "tipo": "markdown",
            "html": mistune.html(prosa_depois)
        })
        
    return resultado

result = renderizar_estrutura("""### Introdução à Perspectiva
A perspectiva é a técnica que **permite** representar...

- Ponto de fuga
- Linha do horizonte

:::exemplo
Observe como Picasso usou linhas diagonais...
:::

:::exercicio
{
  "pergunta": "Quem pintou Guernica?",
  "opcoes": ["Monet", "Picasso"],
  "correta": 1
}
:::
    
:::exemplo
Observe como Picasso usou linhas diagonais...
:::    

:::quebrar_pagina

Quebra a pagina
:::
""")

print(result)
