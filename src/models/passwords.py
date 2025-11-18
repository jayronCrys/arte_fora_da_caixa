#models/passwords.py
import bcrypt as cripto


def make_hash(password):

    try:
        hashPassword = cripto.hashpw(password.encode("utf-8"), cripto.gensalt())
        return hashPassword.decode("utf-8")
    
    except:
        return False
    

def compare_password(passwordIn, password):
    
    if not isinstance(password, bytes):
        password_hash_bytes = password.encode('utf-8')
        
    if not isinstance(passwordIn, bytes):
        passwordIn_hash_bytes = passwordIn.encode('utf-8')
        
    try:
        passwordValidation = cripto.checkpw(passwordIn_hash_bytes, password_hash_bytes) 
        return passwordValidation
    
    except Exception:
        return False