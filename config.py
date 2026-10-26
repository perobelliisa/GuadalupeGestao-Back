import os
from dotenv import load_dotenv

# Lê o .env do diretório do backend quando a aplicação é iniciada.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

SECRET_KEY = os.getenv('SECRET_KEY', 'senha_muito_secreta')
DEBUG = os.getenv('DEBUG', 'true').strip().lower() in ('1', 'true', 'yes', 'on')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv(
    'DB_NAME',
    r'C:\Users\Guilherme kawanami\OneDrive\Documentos\GitHub\GuadalupeGestao-Back\BANCO.FDB',
)
DB_USER = os.getenv('DB_USER', 'SYSDBA')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'sysdba')
UPLOAD_FOLDER = os.getenv(
    'UPLOAD_FOLDER', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'arquivos')
)
AUTH_TOKEN_MAX_AGE = int(os.getenv('AUTH_TOKEN_MAX_AGE', str(5000 * 60)))
