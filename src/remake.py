"""
migrate_add_banner_contenttype.py

Execute UMA VEZ na raiz do projeto:
    python migrate_add_banner_contenttype.py

Adiciona as colunas 'banner' e 'content_type' à tabela 'conteudos'
sem apagar dados existentes.
"""

import sqlite3
import os

# ── Ajuste o caminho do seu banco aqui ───────────────────────────────────────
DB_PATH = os.environ.get("Armazenamento interno/arte_fora_da_caixa/", "arte.db")   # ou "instance/banco.db", etc.
# ─────────────────────────────────────────────────────────────────────────────

def column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def run():
    if not os.path.exists(DB_PATH):
        print(f"[ERRO] Banco não encontrado em: {DB_PATH}")
        print("Ajuste a variável DB_PATH no topo do script.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    added = []

    if not column_exists(cur, "conteudos", "banner"):
        cur.execute("ALTER TABLE conteudos ADD COLUMN banner BLOB")
        added.append("banner")

    if not column_exists(cur, "conteudos", "content_type"):
        cur.execute("ALTER TABLE conteudos ADD COLUMN content_type VARCHAR(50)")
        added.append("content_type")

    if added:
        conn.commit()
        print(f"[OK] Colunas adicionadas: {', '.join(added)}")
    else:
        print("[OK] Colunas já existiam, nada alterado.")

    conn.close()

if __name__ == "__main__":
    run()
