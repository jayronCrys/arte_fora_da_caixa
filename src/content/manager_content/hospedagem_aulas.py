import sqlite3 as sq3
def init_db():
    #---> todo id contido no banco será um uuid, vai ter que ser mudade depois
    conn = sq3.connect("meu_db.db")
    conn.row_factory = sq3.Row
    return conn


def create_bd():
    db = init_db()
    db.execute("""CREATE TABLE IF NOT EXISTS USERS(
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               email TEXT UNIQUE NOT NULL,
               user_name TEXT UNIQUE NOT NULL,
               pass_word TEXT NOT NULL,
               creation_date TEXT DEFAULT CURRENT_TIMESTAMP,
               photo TEXT DEFAULT T 
               )
            """)#---> foto vai ser um caminho para img de ferfil,tem que definir T como um caminho default e adicionar uma img lá.
    db.commit()
    db.close()


def create_db_content():
    db = init_db()
    db.execute("""
CREATE TABLE IF NOT EXISTS CONTENT(
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               publisherId TEXT NOT NULL,
               authorId TEXT NOT NULL,
               contentName TEXT UNIQUE NOT NULL,
               category TEXT NOT NULL,
               contentLvl TEXT NOT NULL,
               creation_date TEXT DEFAULT CURRENT_TIMESTAMP
            """)
   
    db.commit()
    db.close()

def course_to_user():
    db = init_db()
    db.execute("""
CREATE TABLE IF NOT EXISTS CONT_USER(
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               userId TEXT NOT NULL,
               contentId TEXT NOT NULL,
               score INTEGER,
               creation_date TEXT DEFAULT CURRENT_TIMESTAMP
            """)
   
    db.commit()
    db.close()
   