from ...apis.adobe.adobe_conversor import build_api_conversion
import pypandoc
import os
import shutil
import logging
import regex as re
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

WINDOWS_UPLOAD_DIR = os.path.join(SCRIPT_DIR, '..', '..', '..', 'uploads', 'imgs') 

WINDOWS_UPLOAD_DIR_ABS = os.path.abspath(WINDOWS_UPLOAD_DIR)

os.makedirs(WINDOWS_UPLOAD_DIR_ABS, exist_ok=True)
def delete_file(file):
    
    if os.path.exists(file):
        try:  
            os.remove(file)
            logging.info(f"Arquivo {file} apagado com sucesso.")
            
        except Exception as e:
            logging.error(f"Erro ao tentar apagar o arquivo {file} por {e}.")
            
            
def conv_pdf_to_doc(pdf, pdfName):
    temp_dir = tempfile.gettempdir()
    doc = os.path.join(temp_dir, f"{pdfName}.docx")
    doc = doc.replace("C:", "")
    temp_dir = temp_dir.replace("C:", "")
    print("doc:", doc, pdfName)
    print("passei?")
    print(temp_dir)
    if build_api_conversion(pdf, doc): 
        delete_file(pdf)
        return conv_doc_to_html(doc, docName=pdfName)
        
    return None, None

def conv_doc_to_html(docPath, docName):
    
    temp_dir = tempfile.gettempdir()
    
    MEDIA_DIR_TEMPORARIO = os.path.join(temp_dir, f"media_pandoc_{docName}")
    URL_BASE_PUBLICO = r"/uploads/imgs"
    os.makedirs(MEDIA_DIR_TEMPORARIO, exist_ok = True) 
    
    try:

        htmlContent = pypandoc.convert_file(
            docPath, 
            to='html', 
            format='docx',
            extra_args=[f'--extract-media={MEDIA_DIR_TEMPORARIO}']
        ) or None
        
        if htmlContent:

            pandocMediaDir = os.path.join(MEDIA_DIR_TEMPORARIO, 'media')
            
            for fileName in os.listdir(pandocMediaDir):
                tempPath = os.path.join(pandocMediaDir, fileName)
  
                finalFileName = f"{docName}_{fileName}"
                urlFinalWeb = os.path.join(URL_BASE_PUBLICO, finalFileName)
                finalPath = os.path.join(os.environ.get('UPLOAD_DIR', WINDOWS_UPLOAD_DIR_ABS), finalFileName)
                os.rename(tempPath, finalPath)
                htmlContent = re.sub(
                    r'src="media/' + re.escape(fileName) + r'"',
                    f'src="{urlFinalWeb}"',
                    htmlContent
                )

            
            
            delete_file(docPath)
            htmlName = f"{docName}.html"
            print(htmlName, htmlContent)
            return htmlContent, htmlName
       
        return None, None
        
    except Exception as e:
        logging.error(f"Erro ao usar Pandoc: {e}")
        return None, None
        
    finally:
        
        if os.path.exists(MEDIA_DIR_TEMPORARIO):
            shutil.rmtree(MEDIA_DIR_TEMPORARIO)
            logging.info(f"Pasta temporária do Pandoc apagada: {MEDIA_DIR_TEMPORARIO}")