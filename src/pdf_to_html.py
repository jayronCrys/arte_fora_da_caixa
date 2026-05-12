"""
pdf_to_html.py
Extrai texto de um PDF (bytes) e devolve HTML semântico pronto para
ser inserido num template Jinja2.

Heurísticas usadas:
  - Linha toda em maiúsculas  → <h2>
  - Linha com fonte > média   → <h3>
  - Linha começando com •/–/- → <li> dentro de <ul>
  - Linha começando com N.    → <li> dentro de <ol>
  - Linha em branco           → fecha parágrafo atual
  - Resto                     → <p>
  - Tabelas detectadas pelo pdfplumber → <table>
"""

import io
import re
import html as html_lib
from typing import Optional

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


# ── helpers ────────────────────────────────────────────────────────────────────

def _esc(text: str) -> str:
    return html_lib.escape(text)


def _avg_font_size(page) -> float:
    sizes = [
        w.get("size", 12)
        for w in (page.chars or [])
        if w.get("size")
    ]
    return sum(sizes) / len(sizes) if sizes else 12.0


def _line_font_size(line_chars) -> float:
    sizes = [c.get("size", 12) for c in line_chars if c.get("size")]
    return sum(sizes) / len(sizes) if sizes else 12.0


def _is_bold(line_chars) -> bool:
    fonts = [c.get("fontname", "") for c in line_chars]
    return any("Bold" in f or "bold" in f for f in fonts)


# ── extração por página ────────────────────────────────────────────────────────

def _page_to_html(page) -> str:
    avg = _avg_font_size(page)
    blocks: list[str] = []

    # ── tabelas primeiro (pdfplumber detecta automaticamente) ──────────────────
    tables = page.extract_tables()
    table_html_list = []
    for tbl in (tables or []):
        rows_html = []
        for i, row in enumerate(tbl):
            cells = "".join(
                f"<{'th' if i == 0 else 'td'}>{_esc(str(c or ''))}</'{'th' if i == 0 else 'td'}>"
                for c in row
            )
            rows_html.append(f"<tr>{cells}</tr>")
        table_html_list.append(
            f'<div class="pdf-table-wrap"><table class="pdf-table">'
            f"{''.join(rows_html)}</table></div>"
        )

    # ── texto ──────────────────────────────────────────────────────────────────
    # agrupa chars em linhas usando y-coordenada
    chars = page.chars or []
    if not chars:
        return "\n".join(table_html_list)

    # ordena por (top arredondado, x)
    from itertools import groupby
    chars_sorted = sorted(chars, key=lambda c: (round(c["top"] / 3) * 3, c["x0"]))
    lines_raw = []
    for _, grp in groupby(chars_sorted, key=lambda c: round(c["top"] / 3) * 3):
        group = list(grp)
        text = "".join(c.get("text", "") for c in group).strip()
        if text:
            lines_raw.append((text, group))

    in_ul = False
    in_ol = False
    buf_p: list[str] = []          # acumula linhas de parágrafo

    def flush_p():
        nonlocal buf_p
        if buf_p:
            blocks.append(f'<p class="pdf-p">{"<br>".join(buf_p)}</p>')
            buf_p = []

    def close_lists():
        nonlocal in_ul, in_ol
        if in_ul:
            blocks.append("</ul>")
            in_ul = False
        if in_ol:
            blocks.append("</ol>")
            in_ol = False

    for text, line_chars in lines_raw:
        size = _line_font_size(line_chars)
        bold = _is_bold(line_chars)
        escaped = _esc(text)

        # Título grande → h2
        if size >= avg * 1.45 or (size >= avg * 1.2 and text.isupper()):
            flush_p(); close_lists()
            blocks.append(f'<h2 class="pdf-h2">{escaped}</h2>')
            continue

        # Título médio → h3
        if size >= avg * 1.15 or (bold and size >= avg * 1.05):
            flush_p(); close_lists()
            blocks.append(f'<h3 class="pdf-h3">{escaped}</h3>')
            continue

        # Lista não ordenada
        if re.match(r"^[•·▪▸\-–—]\s+", text):
            flush_p()
            if not in_ul:
                close_lists()
                blocks.append('<ul class="pdf-ul">')
                in_ul = True
            item = re.sub(r"^[•·▪▸\-–—]\s+", "", text)
            blocks.append(f"<li>{_esc(item)}</li>")
            continue

        # Lista ordenada  (1. texto  /  a) texto)
        if re.match(r"^\w{1,2}[.)]\s+", text):
            flush_p()
            if not in_ol:
                close_lists()
                blocks.append('<ol class="pdf-ol">')
                in_ol = True
            item = re.sub(r"^\w{1,2}[.)]\s+", "", text)
            blocks.append(f"<li>{_esc(item)}</li>")
            continue

        # Linha em branco → fecha parágrafo
        if not text.strip():
            flush_p()
            continue

        # Linha normal → acumula no parágrafo
        close_lists()
        buf_p.append(escaped)

    flush_p()
    close_lists()

    # intercala tabelas (coloca antes do primeiro bloco de texto, por simplicidade)
    result = table_html_list + blocks
    return "\n".join(result)


# ── entrada pública ────────────────────────────────────────────────────────────

def pdf_bytes_to_html(pdf_bytes: bytes) -> Optional[str]:
    """
    Recebe os bytes de um PDF e retorna uma string HTML.
    Retorna None se pdfplumber não estiver instalado ou der erro.
    """
    print("=====> Entro no pdf_to_html")
    if not HAS_PDFPLUMBER:
        return None
    try:
        pages_html = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                body = _page_to_html(page)
                pages_html.append(
                    f'<div class="pdf-page" data-page="{i}">{body}</div>'
                )
        print("======deu certo, supostamente")
        return "\n".join(pages_html)
    except Exception as exc:
        print(f"[pdf_to_html] erro: {exc}")
        return None
