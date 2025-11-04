import importlib
import subprocess
import sys

def ensure_libs_installed(libs):
    """Verifica e instala automaticamente as bibliotecas listadas."""
    for lib in libs:
        try:
            importlib.import_module(lib)
            print(f"✅ {lib} já está instalada.")
        except ImportError:
            print(f"📦 Instalando {lib}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])
            print(f"✅ {lib} instalada com sucesso!")


libs = ["flask", "bcrypt", "google-auth", "google-auth-oauthlib",
        "requests", "python-dotenv", "regex", "sqlalchemy", "pymongo",
        "bson"]#--> talvez seja melhor mudar flask para fastApi
ensure_libs_installed(libs)