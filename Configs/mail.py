# config.py (exemplo)
import os

SECRET_KEY = os.environ.get('SECRET_KEY', 'uma-chave-secreta-qualquer')
# Configurações do servidor de e‑mail
MAIL_SERVER = 'smtp.gmail.com'            
# servidor SMTP do Gmail
MAIL_PORT = 587
MAIL_USE_TLS = True                       # usar TLS
MAIL_USE_SSL = False                      # não usar SSL junto com TLS
MAIL_USERNAME = os.environ.get('MAIL_USERNAME')  # seu e‑mail
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')  # senha de app (veja abaixo)
MAIL_DEFAULT_SENDER = ('Nome do App', os.environ.get('MAIL_USERNAME'))


