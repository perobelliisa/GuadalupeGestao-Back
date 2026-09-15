from flask import jsonify, make_response, request
from flask_bcrypt import check_password_hash, generate_password_hash

from main import app, con
from function import (
    gerar_token,
    id_usuario_logado,
    ler_inteiro,
    usuario_e_administrador,
    usuario_pode_gerenciar_doacoes,
    verificar_senha
)


@app.route('/usuarios', methods=['GET'])
def listar_usuarios():
    if not usuario_e_administrador():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        cur.execute('''
            SELECT ID_USUARIO, NOME, EMAIL, TIPO, STATUS
            FROM USUARIO
            ORDER BY NOME
        ''')
        registros = cur.fetchall()

        cur.execute('''
            SELECT UP.ID_USUARIO, P.ID_PROJETO, P.NOME
            FROM USUARIO_PROJETO UP
            INNER JOIN PROJETO P ON P.ID_PROJETO = UP.ID_PROJETO
            ORDER BY P.NOME
        ''')
        projetos_por_usuario = {}
        for registro in cur.fetchall():
            id_usuario = registro[0]
            if id_usuario not in projetos_por_usuario:
                projetos_por_usuario[id_usuario] = []
            projetos_por_usuario[id_usuario].append({
                'id_projeto': registro[1],
                'nome': registro[2].strip()
            })

        usuarios = []
        for registro in registros:
            usuario = {
                'id_usuario': registro[0],
                'nome': registro[1].strip(),
                'email': registro[2].strip(),
                'tipo': registro[3],
                'status': registro[4],
                'projetos': projetos_por_usuario.get(registro[0], [])
            }
            usuarios.append(usuario)
        return jsonify({'sucesso': True, 'usuarios': usuarios}), 200
    except Exception as erro:
        return jsonify({'sucesso': False, 'erro': f'Erro ao listar usuários: {erro}'}), 500
    finally:
        cur.close()


@app.route('/projetos', methods=['GET'])
def listar_projetos():
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        cur.execute('SELECT ID_PROJETO, NOME FROM PROJETO ORDER BY NOME')
        projetos = []
        for registro in cur.fetchall():
            projetos.append({
                'id_projeto': registro[0],
                'nome': registro[1].strip()
            })
        return jsonify({'sucesso': True, 'projetos': projetos}), 200
    except Exception as erro:
        return jsonify({'sucesso': False, 'erro': f'Erro ao listar projetos: {erro}'}), 500
    finally:
        cur.close()


@app.route('/minha-conta', methods=['GET', 'PUT'])
def minha_conta():
    id_usuario = id_usuario_logado()
    if not id_usuario:
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        if request.method == 'GET':
            cur.execute('''
                SELECT ID_USUARIO, NOME, EMAIL, TIPO, STATUS
                FROM USUARIO
                WHERE ID_USUARIO = ?
            ''', (id_usuario,))
            usuario = cur.fetchone()
            if not usuario:
                return jsonify({'sucesso': False, 'mensagem': 'Usuário não encontrado.'}), 404
            return jsonify({'sucesso': True, 'usuario': {
                'id_usuario': usuario[0],
                'nome': usuario[1].strip(),
                'email': usuario[2].strip(),
                'tipo': usuario[3],
                'status': usuario[4]
            }}), 200

        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip().lower()
        tipo = ler_inteiro(request.form.get('tipo'))
        status = ler_inteiro(request.form.get('status'))
        if tipo is None or status is None:
            return jsonify({'sucesso': False, 'mensagem': 'Perfil ou status inválido.'}), 400
        if not nome or not email:
            return jsonify({'sucesso': False, 'mensagem': 'Nome e e-mail são obrigatórios.'}), 400
        if tipo not in (0, 1, 2) or status not in (0, 1):
            return jsonify({'sucesso': False, 'mensagem': 'Perfil ou status inválido.'}), 400

        cur.execute('''
            SELECT ID_USUARIO FROM USUARIO
            WHERE LOWER(EMAIL) = LOWER(?) AND ID_USUARIO <> ?
        ''', (email, id_usuario))
        if cur.fetchone():
            return jsonify({'sucesso': False, 'mensagem': 'E-mail já cadastrado.'}), 409

        cur.execute('''
            UPDATE USUARIO SET NOME = ?, EMAIL = ?, TIPO = ?, STATUS = ?
            WHERE ID_USUARIO = ?
        ''', (nome, email, tipo, status, id_usuario))
        con.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Conta atualizada com sucesso!'}), 200
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao atualizar conta: {erro}'}), 500
    finally:
        cur.close()


@app.route('/usuarios/<int:id_usuario>', methods=['PUT'])
def editar_usuario(id_usuario):
    if not usuario_e_administrador():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip().lower()
        tipo = ler_inteiro(request.form.get('tipo'))
        status = ler_inteiro(request.form.get('status'))
        if not nome or not email:
            return jsonify({'sucesso': False, 'mensagem': 'Nome e e-mail são obrigatórios.'}), 400
        if tipo not in (0, 1, 2):
            return jsonify({'sucesso': False, 'mensagem': 'Perfil inválido.'}), 400
        if status not in (0, 1):
            return jsonify({'sucesso': False, 'mensagem': 'Status inválido.'}), 400

        cur.execute('SELECT ID_USUARIO FROM USUARIO WHERE ID_USUARIO = ?', (id_usuario,))
        if not cur.fetchone():
            return jsonify({'sucesso': False, 'mensagem': 'Usuário não encontrado.'}), 404

        cur.execute('''
            SELECT ID_USUARIO FROM USUARIO
            WHERE LOWER(EMAIL) = LOWER(?) AND ID_USUARIO <> ?
        ''', (email, id_usuario))
        if cur.fetchone():
            return jsonify({'sucesso': False, 'mensagem': 'E-mail já cadastrado.'}), 409

        projetos = []
        if tipo == 2:
            for texto_id in request.form.getlist('projetos'):
                id_projeto = ler_inteiro(texto_id)
                if id_projeto is None:
                    return jsonify({'sucesso': False, 'mensagem': 'Projeto inválido.'}), 400
                if id_projeto not in projetos:
                    projetos.append(id_projeto)

            for id_projeto in projetos:
                cur.execute('SELECT ID_PROJETO FROM PROJETO WHERE ID_PROJETO = ?', (id_projeto,))
                if not cur.fetchone():
                    return jsonify({'sucesso': False, 'mensagem': 'Projeto não encontrado.'}), 400

        cur.execute('''
            UPDATE USUARIO SET NOME = ?, EMAIL = ?, TIPO = ?, STATUS = ?
            WHERE ID_USUARIO = ?
        ''', (nome, email, tipo, status, id_usuario))
        cur.execute('DELETE FROM USUARIO_PROJETO WHERE ID_USUARIO = ?', (id_usuario,))
        for id_projeto in projetos:
            cur.execute('''
                INSERT INTO USUARIO_PROJETO(ID_USUARIO, ID_PROJETO)
                VALUES(?, ?)
            ''', (id_usuario, id_projeto))
        con.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Usuário atualizado com sucesso!'}), 200
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao atualizar usuário: {erro}'}), 500
    finally:
        cur.close()


@app.route('/usuarios/<int:id_usuario>', methods=['DELETE'])
def excluir_usuario(id_usuario):
    if not usuario_e_administrador():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        cur.execute('SELECT ID_USUARIO FROM USUARIO WHERE ID_USUARIO = ?', (id_usuario,))
        if not cur.fetchone():
            return jsonify({'sucesso': False, 'mensagem': 'Usuário não encontrado.'}), 404

        cur.execute('SELECT ID_EMPRESTIMO FROM EMPRESTIMO WHERE ID_USUARIO = ?', (id_usuario,))
        if cur.fetchone():
            return jsonify({
                'sucesso': False,
                'mensagem': 'Não é possível excluir um usuário que possui empréstimos cadastrados.'
            }), 409

        cur.execute('DELETE FROM USUARIO_PROJETO WHERE ID_USUARIO = ?', (id_usuario,))
        cur.execute('DELETE FROM USUARIO WHERE ID_USUARIO = ?', (id_usuario,))
        con.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Usuário excluído com sucesso!'}), 200
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao excluir usuário: {erro}'}), 500
    finally:
        cur.close()


@app.route('/cadastro', methods=['POST'])
def cadastro():
    if not usuario_e_administrador():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        tipo = ler_inteiro(request.form.get('tipo', '0'))
        status = ler_inteiro(request.form.get('status', '0'))
        nome = request.form.get('nome', '').strip().lower()
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha')
        conf_senha = request.form.get('conf_senha')
        if tipo not in (0, 1, 2):
            return jsonify({'sucesso': False, 'mensagem': 'Perfil inválido.'}), 400
        if status not in (0, 1):
            return jsonify({'sucesso': False, 'mensagem': 'Status inválido.'}), 400
        if not nome:
            return jsonify({'sucesso': False, 'mensagem': 'Nome é obrigatório.'}), 400
        if not email or not senha:
            return jsonify({'sucesso': False, 'mensagem': 'E-mail e senha são obrigatórios.'}), 400
        if senha != conf_senha:
            return jsonify({'sucesso': False, 'mensagem': 'As senhas não coincidem'}), 400

        erro_senha = verificar_senha(senha)
        if erro_senha:
            return jsonify({'sucesso': False, 'mensagem': erro_senha}), 400

        projetos = []
        if tipo == 2:
            for texto_id in request.form.getlist('projetos'):
                id_projeto = ler_inteiro(texto_id)
                if id_projeto is None:
                    return jsonify({'sucesso': False, 'mensagem': 'Projeto inválido.'}), 400
                if id_projeto not in projetos:
                    projetos.append(id_projeto)
            for id_projeto in projetos:
                cur.execute('SELECT ID_PROJETO FROM PROJETO WHERE ID_PROJETO = ?', (id_projeto,))
                if not cur.fetchone():
                    return jsonify({'sucesso': False, 'mensagem': 'Projeto não encontrado.'}), 400

        cur.execute('SELECT EMAIL FROM USUARIO WHERE EMAIL = ?', (email,))
        if cur.fetchone():
            return jsonify({'sucesso': False, 'mensagem': 'E-mail já cadastrado'}), 409

        senha_hash = generate_password_hash(senha)
        cur.execute('''
            INSERT INTO USUARIO(NOME, EMAIL, TIPO, SENHA_HASH, STATUS)
            VALUES(?, ?, ?, ?, ?)
            RETURNING ID_USUARIO
        ''', (nome.capitalize(), email, tipo, senha_hash, status))
        id_novo_usuario = cur.fetchone()[0]
        for id_projeto in projetos:
            cur.execute('''
                INSERT INTO USUARIO_PROJETO(ID_USUARIO, ID_PROJETO)
                VALUES(?, ?)
            ''', (id_novo_usuario, id_projeto))
        con.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Usuário cadastrado com sucesso!'}), 201
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao criar usuário: {erro}'}), 500
    finally:
        cur.close()


@app.route('/login', methods=['POST'])
def login():
    cur = con.cursor()
    try:
        dados = request.get_json()
        if dados is None:
            dados = {}
        email = str(dados.get('email', '')).strip()
        senha = dados.get('senha')
        if not email or not senha:
            return jsonify({'erro': 'Preencha todos os campos'}), 400

        cur.execute('''
            SELECT ID_USUARIO, NOME, SENHA_HASH, TIPO
            FROM USUARIO
            WHERE LOWER(EMAIL) = LOWER(?)
        ''', (email,))
        usuario = cur.fetchone()
        if not usuario:
            return jsonify({'erro': 'Email não cadastrado'}), 400
        if not check_password_hash(usuario[2], senha):
            return jsonify({'sucesso': False, 'mensagem': 'Email ou senha está incorreta'}), 401

        token = gerar_token(usuario[0])
        nome = usuario[1].strip().split()[0]
        resposta = make_response(jsonify({
            'id_usuario': usuario[0],
            'id_user': usuario[0],
            'nome': nome,
            'tipo': usuario[3],
            'token': token,
            'sucesso': True,
            'mensagem': 'Logado com sucesso!'
        }), 200)
        resposta.set_cookie(
            'access_token', token, httponly=True, secure=False,
            samesite='Lax', path='/', max_age=3600
        )
        return resposta
    except Exception as erro:
        return jsonify({'sucesso': False, 'erro': f'Erro ao login: {erro}'}), 500
    finally:
        cur.close()
