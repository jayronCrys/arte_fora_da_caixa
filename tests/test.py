
from ..src.controller.users.user_default import Management_User_Default, Login_Account, Create_Account
from ..src.controller.users.user_professor import Professor_User
from ..src.controller.users.user_admin import Management_Admins



GOOGLE_LOGIN_METHOD = 'googlee'
LOCAL_LOGIN_METHOD  = 'local'
CRED_STUDENT   = 'aluno'
CRED_PROFESSOR = 'professor'
CRE_ADMIN      = 'admin'

VALID_PASS   = 'senha_teste_123'
INVALID_PASS = '123456'

USER_DEFAULT_TEST_GOOGLE = {
    "name"    : 'google aluno teste',
    "email"   : 'aluno_teste@gmail.com',
    "password": 'senha_teste_123',
    "picture" : 'https://lh3.googleusercontent.com/a/ACg8ocL8oTDfCrgXf3gJeCmAzwBYC8IVbqS2Jk00ACF63I4dabYe7w=s96-c'
}

USER_DEFAULT_TEST_LOCAL  = {
    "name"    : 'local usuario teste',
    "email"   : None,
    "password": 'senha_teste_123',
    "picture" : None
}

USER_DEFAULT_TEST_LOCAL  = {
    "name"    : 'local usuario teste',
    "email"   : None,
    "password": 'senha_teste_123',
    "picture" : None
}

USER_PROFESSOR_TEST_LOCAL  = {
    "name"    : 'local usuario PROF teste',
    "email"   : None,
    "password": 'senha_teste_123',
    "picture" : None
}
USER_ADMIN_TEST_LOCAL  = {
    "name"    : 'local usuario ADMIN teste',
    "email"   : None,
    "password": 'senha_teste_123',
    "picture" : None
}







#INSERÇÃO DE USUŔIOS

def test_create_user():
    def _test_create_user_by_google():
        Login_Account.login()
        pass

    def _test_create_user_by_local():
        pass

    def _test_create_user_by_admin():
        pass



#LOGIN DE USUÁRIOS
def test_login():
    def _test_login_user_by_google():
        pass

    def _test_login_user_by_local():
        pass



#RETORNO DE INFORMAÇÕES DE USUÁRIOS
def test_get_user():

    def _test_get_user_by_id():
        pass

    def _test_get_user_by_admin():
        pass

    def _test_get_user_by_user_name():
        pass


#RETORNO DE UTUALIZAÇÕES DE USUÁRIOS
def test_update_users():

    def _update_user_by_user():
        def _update_user_name():
            pass
        def _update_user_pass():
            pass
        def _update_user_image():
            pass
        def register_user_email():
            pass
        pass

    def _update_user_by_admin():
        def _update_user_name_by_admin():
            pass
        def _update_user_pass_by_admin():
            pass
        def _update_user_cred_by_admin():
            pass
        

    
