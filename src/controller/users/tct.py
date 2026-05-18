
from src.models.database import get_session as database

def get_content_by_id(contentId):
        conn = dataBase()
            
        content = select_info(conn, Contents, "title",title, None)
        
        conteudo = db.session.query(Contents).first()
        print(conteudo.banner)   # None? bytes?
        conn.close()
        return content
        
        
resp = get_content_by_id("Luan santana eu te amopooooooo")        


print(resp.banner)