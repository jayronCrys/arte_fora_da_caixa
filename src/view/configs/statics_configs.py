# src/config/content_config.py
# ─────────────────────────────────────────────────────────────────────────────
# Fonte única de verdade para tipos de conteúdo e banners padrão.
# Importe onde precisar:
#   from src.config.content_config import CONTENT_TYPES, DEFAULT_BANNERS
# ─────────────────────────────────────────────────────────────────────────────

# Cada item: (valor_salvo_no_banco, rótulo_exibido, emoji)
CONTENT_TYPES = [
    ("aula",        "Aula",             "📖"),
    ("exercicio",   "Exercício",        "✏️"),
    ("artigo",      "Artigo",           "📄"),
    ("projeto",     "Projeto",          "🛠️"),
    ("resumo",      "Resumo",           "📝"),
    ("prova",       "Prova / Avaliação","📋"),
    ("outro",       "Outro",            "📦"),
]

# Banners padrão do site.
# "gradient" → CSS usado como background quando não há imagem real.
# "label"    → nome exibido na galeria.
# Adicione quantos quiser; o frontend lê essa lista automaticamente.
DEFAULT_BANNERS = [
    {
        "id": "aurora",
        "src": "src/view/static/Banners/R1.jpg",
        "name": "R1.jpg",
        "label": "Aurora",
    },
    {
    "id" :      "matematica",
    "src":     "src/view/static/Banners/matematica_banner.jpg",
    "name": "matematica_banner.jpg",
    "label":  "matematica",
    },
       {
    "id" :      "biologia",
    "src":     "src/view/static/Banners/biologia_banner.jpg",
    "name": "biologia_banner.jpg",
    "label":  "biologia",
    },
       {
    "id" :      "historia",
    "src":     "src/view/static/Banners/historia_banner.jpg",
    "name": "historia_banner.jpg",
    "label":  "historia",
    },
       {
    "id" :      "portugues",
    "src":     "src/view/static/Banners/portugues_banner.jpg",
    "name": "portugues_banner.jpg",
    "label":  "portugues",
    },
       {
    "id" :      "geografia",
    "src":     "src/view/static/Banners/geografia_banner.jpg",
    "name": "geografia_banner.jpg", 
    "label":  "geografia",
    },
       {
    "id" :      "artes",
    "src":     "src/view/static/Banners/artes_banner.jpg",
    "name": "artes_banner.jpg",
    "label":  "artes",
       },
]

# Especificações do banner para orientar o usuário
BANNER_SPEC = {
    "max_size_mb": 2,
    "recommended_ratio": "16:9",
    "recommended_px": "1280 × 720",
    "accepted_formats": ["jpg", "jpeg", "png", "webp"],
    # O backend vai redimensionar para isso antes de salvar
    "target_width": 1280,
    "target_height": 720,
}
