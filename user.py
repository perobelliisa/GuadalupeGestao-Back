from flask import Flask, jsonify, request, make_response
from flask_bcrypt import generate_password_hash, check_password_hash
import jwt
from main import app, con
from function import verificar_senha, gerar_token

def usuario_e_administrador():
    token = request.cookies.get('access_token')

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

@app.route('/usuarios', methods=['GET'])
def listar_usuarios():
    if not usuario_e_administrador():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        cur.execute(
            """SELECT ID_USUARIO, NOME, EMAIL, TIPO, STATUS
               FROM USUARIO
               ORDER BY NOME""")

        registros_usuarios = cur.fetchall()

        cur.execute(
            """SELECT UP.ID_USUARIO, P.ID_PROJETO, P.NOME
               FROM USUARIO_PROJETO UP
               INNER JOIN PROJETO P ON P.ID_PROJETO = UP.ID_PROJETO
               ORDER BY P.NOME""")

        projetos_por_usuario = {}
        for id_usuario, id_projeto, nome_projeto in cur.fetchall():
            projetos_por_usuario.setdefault(id_usuario, []).append({
                'id_projeto': id_projeto,
                'nome': nome_projeto.strip()
            })

        usuarios = [
            {
                'id_usuario': usuario[0],
                'nome': usuario[1].strip(),
                'email': usuario[2].strip(),
                'tipo': usuario[3],
                'status': usuario[4],
                'projetos': projetos_por_usuario.get(usuario[0], [])
            }
            for usuario in registros_usuarios
        ]

        return jsonify({'sucesso': True, 'usuarios': usuarios}), 200
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': f'Erro ao listar usuários: {e}'}), 500
    finally:
        cur.close()

@app.route('/projetos', methods=['GET'])
def listar_projetos():
    if not usuario_e_administrador():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        cur.execute(
            """SELECT ID_PROJETO, NOME
               FROM PROJETO
               ORDER BY NOME""")

        projetos = [
            {
                'id_projeto': projeto[0],
                'nome': projeto[1].strip()
            }
            for projeto in cur.fetchall()
        ]

        return jsonify({'sucesso': True, 'projetos': projetos}), 200
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': f'Erro ao listar projetos: {e}'}), 500
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

        try:
            tipo = int(request.form.get('tipo'))
            status = int(request.form.get('status'))
        except (TypeError, ValueError):
            return jsonify({'sucesso': False, 'mensagem': 'Perfil ou status inválido.'}), 400

        if not nome or not email:
            return jsonify({'sucesso': False, 'mensagem': 'Nome e e-mail são obrigatórios.'}), 400

        if tipo not in (0, 1, 2):
            return jsonify({'sucesso': False, 'mensagem': 'Perfil inválido.'}), 400

        if status not in (0, 1):
            return jsonify({'sucesso': False, 'mensagem': 'Status inválido.'}), 400

        cur.execute(
            "SELECT ID_USUARIO FROM USUARIO WHERE ID_USUARIO = ?",
            (id_usuario,)
        )
        if not cur.fetchone():
            return jsonify({'sucesso': False, 'mensagem': 'Usuário não encontrado.'}), 404

        cur.execute(
            """SELECT ID_USUARIO
               FROM USUARIO
               WHERE LOWER(EMAIL) = LOWER(?) AND ID_USUARIO <> ?""",
            (email, id_usuario)
        )
        if cur.fetchone():
            return jsonify({'sucesso': False, 'mensagem': 'E-mail já cadastrado.'}), 409

        projetos = []
        if tipo == 2:
            try:
                projetos = list(dict.fromkeys(
                    int(id_projeto)
                    for id_projeto in request.form.getlist('projetos')
                ))
            except (TypeError, ValueError):
                return jsonify({'sucesso': False, 'mensagem': 'Projeto inválido.'}), 400

            for id_projeto in projetos:
                cur.execute(
                    "SELECT ID_PROJETO FROM PROJETO WHERE ID_PROJETO = ?",
                    (id_projeto,)
                )
                if not cur.fetchone():
                    return jsonify({'sucesso': False, 'mensagem': 'Projeto não encontrado.'}), 400

        cur.execute(
            """UPDATE USUARIO
               SET NOME = ?, EMAIL = ?, TIPO = ?, STATUS = ?
               WHERE ID_USUARIO = ?""",
            (nome, email, tipo, status, id_usuario)
        )

        cur.execute(
            "DELETE FROM USUARIO_PROJETO WHERE ID_USUARIO = ?",
            (id_usuario,)
        )

        for id_projeto in projetos:
            cur.execute(
                """INSERT INTO USUARIO_PROJETO(ID_USUARIO, ID_PROJETO)
                   VALUES(?, ?)""",
                (id_usuario, id_projeto)
            )

        con.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Usuário atualizado com sucesso!'}), 200
    except Exception as e:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao atualizar usuário: {e}'}), 500
    finally:
        cur.close()

@app.route('/usuarios/<int:id_usuario>', methods=['DELETE'])
def excluir_usuario(id_usuario):
    if not usuario_e_administrador():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        cur.execute(
            "SELECT ID_USUARIO FROM USUARIO WHERE ID_USUARIO = ?",
            (id_usuario,)
        )
        if not cur.fetchone():
            return jsonify({'sucesso': False, 'mensagem': 'Usuário não encontrado.'}), 404

        cur.execute(
            "DELETE FROM USUARIO_PROJETO WHERE ID_USUARIO = ?",
            (id_usuario,)
        )
        cur.execute(
            "DELETE FROM USUARIO WHERE ID_USUARIO = ?",
            (id_usuario,)
        )

        con.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Usuário excluído com sucesso!'}), 200
    except Exception as e:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao excluir usuário: {e}'}), 500
    finally:
        cur.close()

@app.route('/cadastro', methods=['POST'])
def cadastro():
    if not usuario_e_administrador():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur= con.cursor()
    try:
        tipo= int(request.form.get('tipo', 0))
        nome= request.form.get('nome', '').strip().lower()
        email=  request.form.get('email', '').strip().lower()
        senha= request.form.get('senha')
        status = int(request.form.get('status', 0))
        conf_senha= request.form.get('conf_senha')
        projetos_recebidos = request.form.getlist('projetos')

        if tipo not in (0, 1, 2):
            return jsonify({'sucesso': False, 'mensagem': 'Perfil inválido.'}), 400

        if status not in (0, 1):
            return jsonify({'sucesso': False, 'mensagem': 'Status inválido.'}), 400

        projetos = []
        if tipo == 2:
            try:
                projetos = list(dict.fromkeys(int(id_projeto) for id_projeto in projetos_recebidos))
            except (TypeError, ValueError):
                return jsonify({'sucesso': False, 'mensagem': 'Projeto inválido.'}), 400

            for id_projeto in projetos:
                cur.execute(
                    "SELECT ID_PROJETO FROM PROJETO WHERE ID_PROJETO = ?",
                    (id_projeto,)
                )
                if not cur.fetchone():
                    return jsonify({'sucesso': False, 'mensagem': 'Projeto não encontrado.'}), 400
        
        if not nome or nome.strip() == None:
            return jsonify({'sucesso': False, 'mensagem':'Nome é obrigatório.'}), 400
        
        if not email or email.strip() == None or not senha:
            return jsonify({'sucesso': False, 'mensagem':'E-mail e senha são obrigatórios.'}), 400
        
        erro_senha= verificar_senha(senha)
        
        if erro_senha:
            return jsonify({'sucesso': False, 'mensagem': erro_senha}), 400
        
        if senha != conf_senha:
            return jsonify({'sucesso': False, 'mensagem': 'As senhas não coincidem'})
        
        cur.execute("""
                    SELECT EMAIL
                    FROM USUARIO
                    WHERE EMAIL = ?
                    """, (email,))
        
        conflito= cur.fetchone()
        
        if conflito:
            return jsonify({'sucesso': False, 'mensagem': 'E-mail já cadastrado'})
        
        senha_hash= generate_password_hash(senha)
        
        cur.execute("""
                    INSERT INTO USUARIO(NOME, 
                                        EMAIL,
                                        TIPO,
                                        SENHA_HASH,
                                        STATUS)
                    VALUES(?, ?, ?, ?, ?)
                    RETURNING ID_USUARIO
                    """, (nome.capitalize(), email, tipo, senha_hash, status))

        id_usuario = cur.fetchone()[0]

        for id_projeto in projetos:
            cur.execute(
                """INSERT INTO USUARIO_PROJETO(ID_USUARIO, ID_PROJETO)
                   VALUES(?, ?)""",
                (id_usuario, id_projeto)
            )

        con.commit()
        
        return jsonify({'sucesso': True, 'mensagem' : 'Usuário cadastrado com sucesso!'})
    except Exception as e:
        con.rollback()
        return jsonify({'erro': f'Erro ao criar: {e}'}), 500

    finally:
        cur.close()
        
        
@app.route('/login', methods=['POST'])
def login():
    cur = con.cursor()
    try:
        dados = request.get_json(silent=True) or {}
        email = str(dados.get('email') or '').strip()
        senha = dados.get('senha')

        if not email or not senha:
            return jsonify({'erro': 'Preencha todos os campos'}), 400

        cur.execute(
            """SELECT ID_USUARIO, NOME, SENHA_HASH, TIPO
               FROM USUARIO
               WHERE LOWER(EMAIL) = LOWER(?)""",
            (email,))
        usuario = cur.fetchone()

        if not usuario:
            return jsonify({'erro': 'Email não cadastrado'}), 400

        id_usuario = usuario[0]
        nomeBruto = usuario[1]
        nome = nomeBruto.strip().split()[0]
        senha_hash = usuario[2]
        tipo = usuario[3]

        if check_password_hash(senha_hash, senha):
            token = gerar_token(id_usuario)

            resp = make_response(jsonify({
                'id_usuario': id_usuario,
                'id_user': id_usuario,
                'nome': nome,
                'tipo': tipo,
                'token': token,
                'sucesso': True,
                'mensagem': 'Logado com sucesso!'
            }), 200)

            resp.set_cookie(
                'access_token', token,
                httponly=True,
                secure=False,
                samesite="Lax",
                path="/",
                max_age=3600
            )
            return resp
        else:
            return jsonify({'sucesso':False, 'mensagem': 'Email ou Senha está incorreta'}), 401

    except Exception as e:
        return jsonify({'erro': f'Erro ao login: {e}'}), 500
    finally:
        cur.close()
