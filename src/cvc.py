import subprocess
import tempfile
import mammoth
from mk import parse_html_to_content_list as pth
import os 
def doc_to_pdf(doc_bytes: bytes) -> bytes:
    """Converte .doc para PDF usando LibreOffice headless."""
    with tempfile.NamedTemporaryFile(suffix=".doc", delete=False) as tmp_doc:
        tmp_doc.write(doc_bytes)
        doc_path = tmp_doc.name
    out_dir = tempfile.mkdtemp()
    subprocess.run([
        "libreoffice", "--headless", "--convert-to", "pdf",
        "--outdir", out_dir, doc_path
    ], check=True)
    pdf_path = os.path.join(out_dir, os.path.basename(doc_path).replace(".doc", ".pdf"))
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    # Limpeza dos temporários (pode ser agendada)
    return pdf_bytes

def doc_to_html(doc_bytes: bytes) -> str:
    """Converte .doc para HTML limpo."""
    # 1. Converter .doc -> .docx com LibreOffice
    doc_path = doc_bytes
    with tempfile.NamedTemporaryFile(suffix=".doc", delete=False) as tmp_doc:
        tmp_doc.write(doc_bytes)
        doc_path = tmp_doc.name
        out_dir = tempfile.mkdtemp()
        subprocess.run([
        "libreoffice", "--headless", "--convert-to", "docx",
        "--outdir", out_dir, doc_path
    ], check=True)
        doc_path = os.path.join(out_dir, os.path.basename(doc_path).replace(".doc", ".docx"))
    docx_path = doc_path
    # 2. Mammoth extrai HTML semântico (sem estilo Office)
    with open(docx_path, "rb") as f:
        result = mammoth.convert_to_html(f)
    html = result.value
    # Limpeza de temporários
    
    return html
    
with open("src/Arquivo_doc.docx", "rb") as doc:
    doc = doc.read()

import mammoth
from mk import parse_html_to_content_list as pth

def docx_to_html(docx_bytes: bytes) -> str:
    """Converte .docx para HTML — sem LibreOffice."""
    import io
    result = mammoth.convert_to_html(io.BytesIO(docx_bytes))
    return result.value

with open("src/Arquivo_doc.docx", "rb") as f:
    docx_bytes = f.read()

html = docx_to_html(docx_bytes)
mkw = pth(html)
print(mkw)  
"""html = doc_to_html(doc)
mkw = pth(html)
print(mkw)"""