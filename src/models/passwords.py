#models/passwords.py
import bcrypt as cripto


def make_hash(password):

    try:
        hashPassword = cripto.hashpw(password.encode("utf-8"), cripto.gensalt())
        return hashPassword
    
    except:
        return False
    

def compare_password(user, password):
    password_hash_bytes = user["password"] 
    
    if not isinstance(password_hash_bytes, bytes):
        password_hash_bytes = password_hash_bytes.encode('utf-8')

    try:
        passwordValidation = cripto.checkpw(password.encode("utf-8"), password_hash_bytes) 
        return passwordValidation
    
    except Exception:
        return False