import sqlite3 as sq
import logging
from typing import Union

#b = sq.connect("dh.db")
#c = db.cursor()
#c.execute("""CREATE TABLE IF NOT EXISTS SSS(
#id INTEGER PRIMARY KEY AUTOINCREMENT, 
#name TEXT NOT NULL,
#idade INTEGER NOT NULL)""")

def insert_info(db: sq, table: str, collumns: list,  values: list)->bool:
    
    if isinstance(collumns, list):
        placeholders = ", ".join(["?" for n in range (len(collumns))])
        collumns = ", ".join(collumns)
        conn = db.cursor()
        try:
            
            conn.execute(f"INSERT INTO {table} ({collumns}) VALUES ({placeholders}) ", values)
            db.commit()
            logging.info("Informacao adicionads")
            return True
            
        except Exception as e:
            logging.error(f"Erro ao adocionar informacoes de usuario, motivo {e}")
            db.rollback()
            logging.warning("Dezfazendo alteracoes no banco")
            return False
            
        finally:
            conn.close()
            logging.info("Banco de dados fechado")
        
    logging.warning("A ação de inserção nem foi iniciada pois o tipo de dados informado não atende aos requisitos")
    return False
      
      
def select_info(db: sq, table: str, collumnReference: str, item_to_select: Union[str, list], varReference: list)-> Union[bool, tuple]:
        
    if isinstance(varReference, list):
        if isinstance(item_to_select, list):
            item_to_select = ", ".join(item_to_select)

        conn = db.cursor()

        try:
            response = conn.execute(f"SELECT {item_to_select} FROM {table} WHERE {collumnReference} = ?",
            varReference).fetchone()
            
            db.commit()
            logging.info("seleção bem sucedida")
            return response
        
        except Exception as e:
            logging.error(f"Erro selecionar informacoes de elemento, motivo: {e}")
            db.rollback()
            logging.warning("Dezfazendo alteracoes no banco")
            return False
            
        finally:
            db.close()
            logging.info("Banco de dados fechado")

    logging.warning("A ação de seleção nem foi iniciada pois o tipo de dados informado não atende aos requisitos")
    return False
      

def update_ifo(db: sq, table: str, collumnUpdate: str, collumnReference: str, varReference, newValue)->bool:
    if isinstance(collumnReference, str):
        conn = db.cursor()
        try:
            conn.execute(f"UPDATE {table} SET {collumnUpdate} = ? WHERE {collumnReference} = ?", (newValue, varReference))
            db.commit()
            logging.info("Informacao atualizada")
            return True
            
        except Exception as e:
            logging.error(f"Erro ao atualizar informacoes de usuario: {e}")
            db.rollback()
            logging.warning("Dezfazendo alteracoes no banco")
            return False
            
        finally:
            db.close()
            logging.info("Banco de dados fechado")

    logging.warning("A ação de update nem foi iniciada pois o tipo de dados informado não atende aos requisitos")
    return False    
    

def delete_info(db: sq, table: str, collumnReference: str, valReference: str)->bool:
    

    conn = db.cursor()
    if isinstance(valReference, str):
        try:
            
            conn.execute(f"DELETE FROM {table} WHERE {collumnReference} = ?", (valReference, ))
            db.commit()
            logging.info("Exclusão feitao com sucesso")
            return True
            
        except Exception as e:
            logging.error(f"Erro ao deletar informacoes. Motivo: {e}")
            db.rollback()
            logging.warning("Dezfazendo alteracoes no banco")
            return False
            
        finally:
            db.close()
            logging.info("Banco de dados fechado")

    logging.warning("A ação de deletar nem foi iniciada pois o tipo de dados informado não atende aos requisitos")
    return False
