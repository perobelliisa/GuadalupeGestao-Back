import datetime
import jwt

senha_secreta = "senha_muito_secreta"

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

