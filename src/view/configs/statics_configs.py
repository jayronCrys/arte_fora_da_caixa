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
        "src": "/view/static/Banners/R1.jpg",
        "label": "Aurora",
        "gradient": "linear-gradient(135deg, #ff7a00 0%, #00c853 100%)",
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
