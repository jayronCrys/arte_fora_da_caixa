
from .conversor_files import conv_pdf_to_doc, conv_doc_to_html
import os
import webbrowser

def conversor(filePath):
    
    htmlContent, htmlContentName = None, None
    file = os.path.basename(filePath)
    print("pdf: ", file)
    fileName, extension = os.path.splitext(file)
    print(fileName, extension)
    extension = extension.lower().lstrip(".")
    
    if extension == 'pdf' :
        htmlContent, htmlContentName = conv_pdf_to_doc(filePath, fileName)
        
    if extension in ['doc', 'docx'] : 
        htmlContent, htmlContentName = conv_doc_to_html(filePath, fileName)
        
    return htmlContent, htmlContentName


re = conversor(r"\Users\Jaymelo\Downloads\mudaqueemelhor\src\content\assembler_content\relatorio_final.pdf")
with open("pagina.html", "w") as file:
    file.write(re[0])
    
# Abre o arquivo no navegador
webbrowser.open_new_tab("pagina.html")