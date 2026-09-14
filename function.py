import os

from flask import request
from main import app, con
import datetime
import jwt
from werkzeug.utils import secure_filename

# Usa a mesma chave do Flask para criar e validar o token de login.
senha_secreta = app.config['SECRET_KEY']
EXTENSOES_PERMITIDAS = {'.pdf', '.jpg', '.jpeg', '.png'}


def salvar_anexo(arquivo, pasta, prefixo, identificador):
    """Salva um comprovante usando o identificador do registro no nome."""
    if not arquivo or not arquivo.filename:
        return None

    nome_original = secure_filename(arquivo.filename)
    extensao = os.path.splitext(nome_original)[1].lower()
    if extensao not in EXTENSOES_PERMITIDAS:
        raise ValueError('Envie um arquivo PDF, JPG ou PNG.')

    destino = os.path.join(app.config['UPLOAD_FOLDER'], pasta)
    os.makedirs(destino, exist_ok=True)
    nome_arquivo = f'{prefixo}_{identificador}{extensao}'
    arquivo.save(os.path.join(destino, nome_arquivo))
    return f'{pasta}/{nome_arquivo}'

def verificar_senha(senha):
    if len(senha) < 10:
        return "A senha deve ter no mínimo 10 caracteres"

    tem_maiuscula = False
    tem_minuscula = False
    tem_numero = False
    tem_simbolo = False
    simbolos = "!@#$%^&*()_+-=[]}{|;:,.<>?"

    for letra in senha:
        if letra.isupper():
            tem_maiuscula = True
        elif letra.islower():
            tem_minuscula = True
        elif letra.isdigit():
            tem_numero = True
        elif letra in simbolos:
            tem_simbolo = True

    if not tem_maiuscula: return "Falta uma letra maiúscula"
    if not tem_minuscula: return "Falta uma letra minúscula"
    if not tem_numero:    return "Falta um número"
    if not tem_simbolo:   return "Falta um símbolo especial"
    return None

def gerar_token(id_user):
    # Monta os dados que serão salvos dentro do token.
    payload = {
        # Salva o ID do usuário no token.
        'id_user': id_user,
        # Salva o horário de criação do token.
        'timestamp': datetime.datetime.utcnow().isoformat(),
        # Define o horário de expiração do token.
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=5000)
    }
    # Gera o token JWT usando a chave secreta e o algoritmo HS256.
    token = jwt.encode(payload, senha_secreta, algorithm='HS256')
    # Retorna o token gerado.
    return token


def _token_da_requisicao():
    """Obtém o JWT pelo cookie ou pelo cabeçalho Authorization: Bearer <token>."""
    token = request.cookies.get('access_token')
    if token:
        return token

    autorizacao = request.headers.get('Authorization', '')
    if autorizacao.startswith('Bearer '):
        return autorizacao[7:].strip()
    return None


def usuario_e_administrador():
    token = _token_da_requisicao()

    if not token:
        return False

    try:
        payload = jwt.decode(
            token,
            app.config['SECRET_KEY'],
            algorithms=['HS256']
        )
        id_usuario = payload.get('id_user')

        if not id_usuario:
            return False

        cur = con.cursor()
        try:
            cur.execute(
                """SELECT TIPO
                   FROM USUARIO
                   WHERE ID_USUARIO = ?""",
                (id_usuario,)
            )
            usuario = cur.fetchone()
            return bool(usuario and usuario[0] == 0)
        finally:
            cur.close()
    except jwt.PyJWTError:
        return False


def usuario_pode_gerenciar_doacoes():
    """Autoriza os perfis financeiro (0) e doador (1)."""
    token = _token_da_requisicao()
    if not token:
        return False

    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        id_usuario = payload.get('id_user')
        if not id_usuario:
            return False

        cur = con.cursor()
        try:
            cur.execute("SELECT TIPO FROM USUARIO WHERE ID_USUARIO = ?", (id_usuario,))
            usuario = cur.fetchone()
            return bool(usuario and usuario[0] in (0, 1))
        finally:
            cur.close()
    except jwt.PyJWTError:
        return False

