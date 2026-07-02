#models/passwords.py
import logging
import bcrypt as cripto

logger = logging.getLogger(__name__)


def make_hash(password):
    try:
        hashPassword = cripto.hashpw(password.encode("utf-8"), cripto.gensalt())
        return hashPassword.decode("utf-8")

    except Exception as e:
        # Nunca logar o valor da senha em si — só o tipo/contexto do erro.
        logger.error(f"Erro ao gerar hash de senha: {type(e).__name__}: {e}")
        return False


def compare_password(passwordIn, password):
    """
    Compara uma senha em texto puro (passwordIn) com um hash já armazenado
    (password). Corrigido: antes, se `password` ou `passwordIn` já chegassem
    como bytes (em vez de str), a variável correspondente nunca era atribuída
    (só era atribuída dentro do `if not isinstance(..., bytes)`), o que
    lançava UnboundLocalError — silenciosamente capturado pelo `except`
    genérico e tratado como "senha incorreta". Ou seja: login/alteração de
    senha falhava sempre que o valor já vinha em bytes, sem nenhum log
    indicando a causa real.
    """
    try:
        password_bytes = password if isinstance(password, bytes) else password.encode("utf-8")
        passwordIn_bytes = passwordIn if isinstance(passwordIn, bytes) else passwordIn.encode("utf-8")
        return cripto.checkpw(passwordIn_bytes, password_bytes)

    except Exception as e:
        # Idem: nunca logar as senhas, só o tipo do erro para diagnóstico.
        logger.error(f"Erro ao comparar senha: {type(e).__name__}: {e}")
        return False