# config.py (exemplo)
import os
from dotenv import load_dotenv # type: ignore

load_dotenv()
#SECRET_KEY = os.environ.get('SECRET_KEY', 'uma-chave-secreta-qualquer')
# Configurações do servidor de e‑mail
MAIL_SERVER = 'smtp.gmail.com'            
# servidor SMTP do Gmail
MAIL_PORT = 587
MAIL_USE_TLS = True                       # usar TLS
MAIL_USE_SSL = False                      # não usar SSL junto com TLS
MAIL_USERNAME = os.environ.get('MAIL_NAME')  # seu e‑mail
MAIL_PASSWORD = os.environ.get('MAIL_PASS')  # senha de app (veja abaixo)
MAIL_DEFAULT_SENDER = ('Nome do App', os.environ.get('EMAIL'))
print(os.getenv("MAIL_NAME"))
print(MAIL_DEFAULT_SENDER, MAIL_PASSWORD, MAIL_PORT, MAIL_SERVER)



def mail_message(code)->str:
    return f"""Olá,
            Você solicitou a redefinição de senha. Use o código abaixo para continuar:\n
            {code}\n
            Se você não solicitou isso, ignore este e‑mail.
            """
    
