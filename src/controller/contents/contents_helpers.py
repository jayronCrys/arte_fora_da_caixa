
class ContentsHelpers:
    
    def content_exists(content):
        @wraps(content)
        def wrapper(self,  *args, **kwargs):
            conn = self.dataBase()
            try:
                content = select_info(
                    conn,
                    Contents,
                    "id",
                    UUID(str(contentId)),
                    ["id", "title", "desc", "banner", "content_type", "author", "creation_date", "publisher_id"]
                )
                sucesfull_log(f"[GET_CONTENT_BY_ID]: conteúdo retornado com sucesso {content['id']}")
                return content
                
            except Exception as e:
                error_log(f"[GET_CONTENT_BY_ID]: Erro ao obter conteúdo por ID {contentId}: {e}")
                return False            
            finally:
                conn.close()
                content_return = content(self, *args, **kwargs)
        
    @content_exists
    @Login_Account.is_loged            
    def get_my_courses(self) -> list: 
        inscriptions = self.my_inscriptions()
        if not inscriptions:
            return []
            
        my_courses = []
        for inscription in inscriptions:
            content_id = inscription["content_id"]
            # Ajustado para usar o nome do método corrigido em snake_case
            course = self.GET_FULL_CONTENT(all_contents=False, content_to_select=content_id, review=True)
            
            if course and len(course) > 0:
                my_courses.append(course[0])
                    
        return my_courses
        
    @Login_Account.is_loged   
    def get_content_by_id(self, contentId: str):
        

    @Login_Account.is_loged
    def get_all_contents(self) -> Union[list, bool]:
        conn = self.dataBase()
        try:
            all_contents = conn.query(Contents).all()
            return [{
                "id":            str(c.id),
                "title":         c.title,
                "desc":          c.desc,
                "banner":        c.banner,
                "content_type":  c.content_type,
                "author":        c.author,
                "creation_date": c.creation_date,
                "publisher_id":  str(c.publisher_id),
            } for c in all_contents]
        except Exception as e:
            logger.error(f"Erro ao listar todos os conteúdos: {e}")
            return False
        finally:            
            conn.close()
            
    @Login_Account.is_loged            
    def get_content_by_name(self, content_name):
        
        if not content_name:
            return []
            
        conn = self.dataBase()
        # 1ª Tentativa: Busca exata
        results = conn.query(Contents).filter_by(title=content_name).all()
        
        # 2ª Tentativa: Se não achou nada na busca exata, busca por aproximação direto no banco
        if not results:
            results = conn.query(Contents).filter(Contents.title.contains(content_name)).all()
        temp_list = []
        for result in results:
            temp_json = {
            "id": str(result.id),
            "title": result.title,
            "desc": result.desc,
            "author": result.author
            }
            temp_list.append(temp_json)
                        
        return temp_list


    @Login_Account.is_loged
    def GET_FULL_CONTENT(self, all_contents=False, content_to_select=None, review=False) -> Union[list, bool]:
        # Corrigido nome para snake_case conforme PEP 8
        if not all_contents and content_to_select:
            contents = [self.get_content_by_id(content_to_select)]
        elif all_contents and content_to_select is None:
            contents = self.get_all_contents()
        else:
            return False
            
        full_content = []
        for content in contents:
            if not content:
                continue
                
            content_id = content["id"]
            if review:
                content["rating"] = self.get_content_review(content_id)
            
            full_content.append(content)
            check_task("RETORNO DE GET FULL CONTENT")
            check_task(full_content)
        return full_content