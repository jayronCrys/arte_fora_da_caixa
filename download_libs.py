import subprocess
import sys
import os

def install_requirements(file_path="requirements.txt"):
    """
    Executa o comando 'pip install -r <arquivo>' para instalar dependências.

    Args:
        file_path (str): O caminho para o arquivo de requisitos.
    """
    
    if not os.path.exists(file_path):
        print(f"erro: O arquivo '{file_path}' não foi encontrado.")
        print("Verifique se o arquivo está no mesmo diretório ou verifique o caminho.")
        return
    
    command = [sys.executable, "-m", "pip", "install", "-r", file_path]
    print(f" Iniciando a instalação das dependências a partir de '{file_path}'...")
    
    try:
        process = subprocess.run(
            command, 
            check=True,
            capture_output=True, 
            text=True
        )
        
        print("instalação concluída com sucesso!")
 
        
    except subprocess.CalledProcessError as e:
        print(f" Erro durante a instalação do PIP. Código de retorno: {e.returncode}")
        print("\n--- Mensagem de Erro ---\n")
        print(e.stderr)
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

if __name__ == "__main__":
    install_requirements()