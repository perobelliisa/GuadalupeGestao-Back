# Este módulo define as configurações usadas pela aplicação, pelo banco e pelos uploads.
# Importa o módulo os para disponibilizar seus recursos.
import os
# Atribui a variável 'SECRET_KEY' o resultado da expressão '"senha_muito_secreta"'.
SECRET_KEY = "senha_muito_secreta"
# Atribui a variável 'DEBUG' o resultado da expressão 'True'.
DEBUG = True
# Atribui a variável 'DB_HOST' o resultado da expressão ''localhost''.
DB_HOST = 'localhost'
# Atribui a variável 'DB_NAME' o resultado da expressão 'r'C:\Users\Guilherme kawanami\OneDrive\Documentos\GitHub\GuadalupeGestao-Back\BANCO.FDB''.
DB_NAME = r'C:\Users\Guilherme kawanami\OneDrive\Documentos\GitHub\GuadalupeGestao-Back\BANCO.FDB'

# Atribui a variável 'DB_USER' o resultado da expressão ''SYSDBA''.
DB_USER = 'SYSDBA'
# Atribui a variável 'DB_PASSWORD' o resultado da expressão ''sysdba''.
DB_PASSWORD = 'sysdba'

# Atribui a variável 'UPLOAD_FOLDER' o resultado da expressão 'os.path.join(os.path.dirname(os.path.abspath(__file__)), 'arquivos')'.
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'arquivos')
