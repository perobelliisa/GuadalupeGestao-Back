import os
SECRET_KEY = "senha_muito_secreta"
DEBUG = True
DB_HOST = 'localhost'
DB_NAME = r'C:\Users\Guilherme kawanami\OneDrive\Documentos\GitHub\GuadalupeGestao-Back\BANCO.FDB'

DB_USER = 'SYSDBA'
DB_PASSWORD = 'sysdba'

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'arquivos')
