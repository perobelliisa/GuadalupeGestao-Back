# Importa jsonify, make_response, request do módulo flask para uso neste arquivo.
from flask import jsonify, make_response, request
# Importa check_password_hash, generate_password_hash do módulo flask_bcrypt para uso neste arquivo.
from flask_bcrypt import check_password_hash, generate_password_hash

# Importa app, con do módulo main para uso neste arquivo.
from main import app, con
# Inicia a importação de vários recursos do módulo function.
from function import (
    # Disponibiliza o recurso gerar_token para as funções deste módulo.
    gerar_token,
    # Disponibiliza o recurso id_usuario_logado para as funções deste módulo.
    id_usuario_logado,
    # Disponibiliza o recurso ler_inteiro para as funções deste módulo.
    ler_inteiro,
    # Disponibiliza o recurso usuario_e_administrador para as funções deste módulo.
    usuario_e_administrador,
    # Disponibiliza o recurso usuario_pode_gerenciar_doacoes para as funções deste módulo.
    usuario_pode_gerenciar_doacoes,
    # Disponibiliza o recurso verificar_senha para as funções deste módulo.
    verificar_senha
# Fecha a chamada ou a lista de argumentos iniciada anteriormente.
)


# Registra o endpoint '/usuarios', methods=['GET'], associando a URL aos métodos HTTP informados.
@app.route('/usuarios', methods=['GET'])
# Define a função listar_usuarios, que lista os usuários e os projetos associados.
def listar_usuarios():
    # Verifica se o usuário autenticado é administrador.
    if not usuario_e_administrador():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Inicia a execução da consulta ou comando SQL no banco de dados.
        cur.execute('''
            SELECT ID_USUARIO, NOME, EMAIL, TIPO, STATUS -- Inicia a seleção dos campos solicitados.
            FROM USUARIO -- Define a tabela USUARIO da consulta.
            ORDER BY NOME -- Ordena os registros pelos campos indicados.
        ''')  # Fecha a string SQL usada pela consulta.
        # Obtém todos os registros e os armazena em 'registros'.
        registros = cur.fetchall()

        # Inicia a execução da consulta ou comando SQL no banco de dados.
        cur.execute('''
            SELECT UP.ID_USUARIO, P.ID_PROJETO, P.NOME -- Inicia a seleção dos campos solicitados.
            FROM USUARIO_PROJETO UP -- Define a tabela USUARIO_PROJETO da consulta.
            INNER JOIN PROJETO P ON P.ID_PROJETO = UP.ID_PROJETO -- Relaciona apenas registros que possuem correspondência na tabela associada.
            ORDER BY P.NOME -- Ordena os registros pelos campos indicados.
        ''')  # Fecha a string SQL usada pela consulta.
        # Inicializa o dicionário 'projetos_por_usuario' vazio.
        projetos_por_usuario = {}
        # Percorre registro in cur.fetchall().
        for registro in cur.fetchall():
            # Atribui a variável 'id_usuario' o resultado da expressão 'registro[0]'.
            id_usuario = registro[0]
            # Verifica se id_usuario not in projetos_por_usuario.
            if id_usuario not in projetos_por_usuario:
                # Inicializa a lista 'projetos_por_usuario[id_usuario]' vazia.
                projetos_por_usuario[id_usuario] = []
            # Adiciona o item atual à lista acumulada.
            projetos_por_usuario[id_usuario].append({
                # Preenche o campo 'id_projeto' do objeto ou resposta que está sendo montado.
                'id_projeto': registro[1],
                # Preenche o campo 'nome' do objeto ou resposta que está sendo montado.
                'nome': registro[2].strip()
            # Fecha a estrutura da resposta e conclui o retorno HTTP.
            })

        # Inicializa a lista 'usuarios' vazia.
        usuarios = []
        # Percorre registro in registros.
        for registro in registros:
            # Inicia o dicionário 'usuario' que armazenará os dados da resposta.
            usuario = {
                # Preenche o campo 'id_usuario' do objeto ou resposta que está sendo montado.
                'id_usuario': registro[0],
                # Preenche o campo 'nome' do objeto ou resposta que está sendo montado.
                'nome': registro[1].strip(),
                # Preenche o campo 'email' do objeto ou resposta que está sendo montado.
                'email': registro[2].strip(),
                # Preenche o campo 'tipo' do objeto ou resposta que está sendo montado.
                'tipo': registro[3],
                # Preenche o campo 'status' do objeto ou resposta que está sendo montado.
                'status': registro[4],
                # Preenche o campo 'projetos' do objeto ou resposta que está sendo montado.
                'projetos': projetos_por_usuario.get(registro[0], [])
            # Fecha o dicionário que está sendo montado.
            }
            # Adiciona o item atual à lista acumulada.
            usuarios.append(usuario)
        # Retorna uma resposta JSON de sucesso com status HTTP 200.
        return jsonify({'sucesso': True, 'usuarios': usuarios}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao listar usuários: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/projetos', methods=['GET'], associando a URL aos métodos HTTP informados.
@app.route('/projetos', methods=['GET'])
# Define a função listar_projetos, que lista os projetos disponíveis.
def listar_projetos():
    # Verifica se o usuário possui permissão para acessar este módulo.
    if not usuario_pode_gerenciar_doacoes():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Executa no banco a consulta SQL 'SELECT ID_PROJETO, NOME FROM PROJETO ORDER BY NOME'.
        cur.execute('SELECT ID_PROJETO, NOME FROM PROJETO ORDER BY NOME')
        # Inicializa a lista 'projetos' vazia.
        projetos = []
        # Percorre registro in cur.fetchall().
        for registro in cur.fetchall():
            # Adiciona o item atual à lista acumulada.
            projetos.append({
                # Preenche o campo 'id_projeto' do objeto ou resposta que está sendo montado.
                'id_projeto': registro[0],
                # Preenche o campo 'nome' do objeto ou resposta que está sendo montado.
                'nome': registro[1].strip()
            # Fecha a estrutura da resposta e conclui o retorno HTTP.
            })
        # Retorna uma resposta JSON de sucesso com status HTTP 200.
        return jsonify({'sucesso': True, 'projetos': projetos}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao listar projetos: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/minha-conta', methods=['GET', 'PUT'], associando a URL aos métodos HTTP informados.
@app.route('/minha-conta', methods=['GET', 'PUT'])
# Define a função minha_conta, que consulta ou atualiza os dados da conta do usuário autenticado.
def minha_conta():
    # Atribui a variável 'id_usuario' o resultado da expressão 'id_usuario_logado()'.
    id_usuario = id_usuario_logado()
    # Verifica se a condição id_usuario é falsa.
    if not id_usuario:
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Seleciona o fluxo de acordo com o método HTTP usado na requisição.
        if request.method == 'GET':
            # Inicia a execução da consulta ou comando SQL no banco de dados.
            cur.execute('''
                SELECT ID_USUARIO, NOME, EMAIL, TIPO, STATUS -- Inicia a seleção dos campos solicitados.
                FROM USUARIO -- Define a tabela USUARIO da consulta.
                WHERE ID_USUARIO = ? -- Filtra os registros conforme a condição informada.
            ''', (id_usuario,))  # Fecha a string SQL usada pela consulta.
            # Obtém um valor do primeiro registro e o armazena em 'usuario'.
            usuario = cur.fetchone()
            # Verifica se a condição usuario é falsa.
            if not usuario:
                # Retorna uma resposta JSON de erro com status HTTP 404.
                return jsonify({'sucesso': False, 'mensagem': 'Usuário não encontrado.'}), 404
            # Inicia a resposta JSON que será devolvida por este endpoint.
            return jsonify({'sucesso': True, 'usuario': {
                # Preenche o campo 'id_usuario' do objeto ou resposta que está sendo montado.
                'id_usuario': usuario[0],
                # Preenche o campo 'nome' do objeto ou resposta que está sendo montado.
                'nome': usuario[1].strip(),
                # Preenche o campo 'email' do objeto ou resposta que está sendo montado.
                'email': usuario[2].strip(),
                # Preenche o campo 'tipo' do objeto ou resposta que está sendo montado.
                'tipo': usuario[3],
                # Preenche o campo 'status' do objeto ou resposta que está sendo montado.
                'status': usuario[4]
            # Fecha a estrutura da resposta e conclui o retorno HTTP.
            }}), 200

        # Remove espaços extras das extremidades do texto.
        nome = request.form.get('nome', '').strip()
        # Remove espaços extras das extremidades do texto.
        email = request.form.get('email', '').strip().lower()
        # Atribui a variável 'tipo' o resultado da expressão 'ler_inteiro(request.form.get('tipo'))'.
        tipo = ler_inteiro(request.form.get('tipo'))
        # Atribui a variável 'status' o resultado da expressão 'ler_inteiro(request.form.get('status'))'.
        status = ler_inteiro(request.form.get('status'))
        # Verifica se tipo is None or status is None.
        if tipo is None or status is None:
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': 'Perfil ou status inválido.'}), 400
        # Verifica se a condição nome or not email é falsa.
        if not nome or not email:
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': 'Nome e e-mail são obrigatórios.'}), 400
        # Verifica se tipo not in (0, 1, 2) or status not in (0, 1).
        if tipo not in (0, 1, 2) or status not in (0, 1):
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': 'Perfil ou status inválido.'}), 400

        # Inicia a execução da consulta ou comando SQL no banco de dados.
        cur.execute('''
            SELECT ID_USUARIO FROM USUARIO -- Inicia a seleção dos campos solicitados.
            WHERE LOWER(EMAIL) = LOWER(?) AND ID_USUARIO <> ? -- Filtra os registros conforme a condição informada.
        ''', (email, id_usuario))  # Fecha a string SQL usada pela consulta.
        # Verifica se cur.fetchone().
        if cur.fetchone():
            # Retorna uma resposta JSON de erro com status HTTP 409.
            return jsonify({'sucesso': False, 'mensagem': 'E-mail já cadastrado.'}), 409

        # Inicia a execução da consulta ou comando SQL no banco de dados.
        cur.execute('''
            UPDATE USUARIO SET NOME = ?, EMAIL = ?, TIPO = ?, STATUS = ? -- Inicia a atualização de um registro existente.
            WHERE ID_USUARIO = ? -- Filtra os registros conforme a condição informada.
        ''', (nome, email, tipo, status, id_usuario))  # Fecha a string SQL usada pela consulta.
        # Confirma definitivamente as alterações feitas na transação.
        con.commit()
        # Retorna uma resposta JSON de sucesso com status HTTP 200.
        return jsonify({'sucesso': True, 'mensagem': 'Conta atualizada com sucesso!'}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Desfaz as alterações da transação após uma falha.
        con.rollback()
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao atualizar conta: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/usuarios/<int:id_usuario>', methods=['PUT'], associando a URL aos métodos HTTP informados.
@app.route('/usuarios/<int:id_usuario>', methods=['PUT'])
# Define a função editar_usuario, que atualiza os dados e os projetos vinculados a um usuário.
def editar_usuario(id_usuario):
    # Verifica se o usuário autenticado é administrador.
    if not usuario_e_administrador():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Remove espaços extras das extremidades do texto.
        nome = request.form.get('nome', '').strip()
        # Remove espaços extras das extremidades do texto.
        email = request.form.get('email', '').strip().lower()
        # Atribui a variável 'tipo' o resultado da expressão 'ler_inteiro(request.form.get('tipo'))'.
        tipo = ler_inteiro(request.form.get('tipo'))
        # Atribui a variável 'status' o resultado da expressão 'ler_inteiro(request.form.get('status'))'.
        status = ler_inteiro(request.form.get('status'))
        # Verifica se a condição nome or not email é falsa.
        if not nome or not email:
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': 'Nome e e-mail são obrigatórios.'}), 400
        # Verifica se tipo not in (0, 1, 2).
        if tipo not in (0, 1, 2):
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': 'Perfil inválido.'}), 400
        # Verifica se status not in (0, 1).
        if status not in (0, 1):
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': 'Status inválido.'}), 400

        # Executa no banco a consulta SQL 'SELECT ID_USUARIO FROM USUARIO WHERE ID_USUARIO = ?'.
        cur.execute('SELECT ID_USUARIO FROM USUARIO WHERE ID_USUARIO = ?', (id_usuario,))
        # Verifica se a condição cur.fetchone() é falsa.
        if not cur.fetchone():
            # Retorna uma resposta JSON de erro com status HTTP 404.
            return jsonify({'sucesso': False, 'mensagem': 'Usuário não encontrado.'}), 404

        # Inicia a execução da consulta ou comando SQL no banco de dados.
        cur.execute('''
            SELECT ID_USUARIO FROM USUARIO -- Inicia a seleção dos campos solicitados.
            WHERE LOWER(EMAIL) = LOWER(?) AND ID_USUARIO <> ? -- Filtra os registros conforme a condição informada.
        ''', (email, id_usuario))  # Fecha a string SQL usada pela consulta.
        # Verifica se cur.fetchone().
        if cur.fetchone():
            # Retorna uma resposta JSON de erro com status HTTP 409.
            return jsonify({'sucesso': False, 'mensagem': 'E-mail já cadastrado.'}), 409

        # Inicializa a lista 'projetos' vazia.
        projetos = []
        # Verifica se tipo == 2.
        if tipo == 2:
            # Percorre texto_id in request.form.getlist('projetos').
            for texto_id in request.form.getlist('projetos'):
                # Atribui a variável 'id_projeto' o resultado da expressão 'ler_inteiro(texto_id)'.
                id_projeto = ler_inteiro(texto_id)
                # Verifica se id_projeto is None.
                if id_projeto is None:
                    # Retorna uma resposta JSON de erro com status HTTP 400.
                    return jsonify({'sucesso': False, 'mensagem': 'Projeto inválido.'}), 400
                # Verifica se id_projeto not in projetos.
                if id_projeto not in projetos:
                    # Adiciona o item atual à lista acumulada.
                    projetos.append(id_projeto)

            # Percorre id_projeto in projetos.
            for id_projeto in projetos:
                # Executa no banco a consulta SQL 'SELECT ID_PROJETO FROM PROJETO WHERE ID_PROJETO = ?'.
                cur.execute('SELECT ID_PROJETO FROM PROJETO WHERE ID_PROJETO = ?', (id_projeto,))
                # Verifica se a condição cur.fetchone() é falsa.
                if not cur.fetchone():
                    # Retorna uma resposta JSON de erro com status HTTP 400.
                    return jsonify({'sucesso': False, 'mensagem': 'Projeto não encontrado.'}), 400

        # Inicia a execução da consulta ou comando SQL no banco de dados.
        cur.execute('''
            UPDATE USUARIO SET NOME = ?, EMAIL = ?, TIPO = ?, STATUS = ? -- Inicia a atualização de um registro existente.
            WHERE ID_USUARIO = ? -- Filtra os registros conforme a condição informada.
        ''', (nome, email, tipo, status, id_usuario))  # Fecha a string SQL usada pela consulta.
        # Executa no banco a consulta SQL 'DELETE FROM USUARIO_PROJETO WHERE ID_USUARIO = ?'.
        cur.execute('DELETE FROM USUARIO_PROJETO WHERE ID_USUARIO = ?', (id_usuario,))
        # Percorre id_projeto in projetos.
        for id_projeto in projetos:
            # Inicia a execução da consulta ou comando SQL no banco de dados.
            cur.execute('''
                INSERT INTO USUARIO_PROJETO(ID_USUARIO, ID_PROJETO) -- Inicia a inclusão de um novo registro.
                VALUES(?, ?) -- Define os valores que serão gravados.
            ''', (id_usuario, id_projeto))  # Fecha a string SQL usada pela consulta.
        # Confirma definitivamente as alterações feitas na transação.
        con.commit()
        # Retorna uma resposta JSON de sucesso com status HTTP 200.
        return jsonify({'sucesso': True, 'mensagem': 'Usuário atualizado com sucesso!'}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Desfaz as alterações da transação após uma falha.
        con.rollback()
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao atualizar usuário: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/usuarios/<int:id_usuario>', methods=['DELETE'], associando a URL aos métodos HTTP informados.
@app.route('/usuarios/<int:id_usuario>', methods=['DELETE'])
# Define a função excluir_usuario, que remove um usuário após verificar seus vínculos.
def excluir_usuario(id_usuario):
    # Verifica se o usuário autenticado é administrador.
    if not usuario_e_administrador():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Executa no banco a consulta SQL 'SELECT ID_USUARIO FROM USUARIO WHERE ID_USUARIO = ?'.
        cur.execute('SELECT ID_USUARIO FROM USUARIO WHERE ID_USUARIO = ?', (id_usuario,))
        # Verifica se a condição cur.fetchone() é falsa.
        if not cur.fetchone():
            # Retorna uma resposta JSON de erro com status HTTP 404.
            return jsonify({'sucesso': False, 'mensagem': 'Usuário não encontrado.'}), 404

        # Executa no banco a consulta SQL 'SELECT ID_EMPRESTIMO FROM EMPRESTIMO WHERE ID_USUARIO = ?'.
        cur.execute('SELECT ID_EMPRESTIMO FROM EMPRESTIMO WHERE ID_USUARIO = ?', (id_usuario,))
        # Verifica se cur.fetchone().
        if cur.fetchone():
            # Inicia a resposta JSON que será devolvida por este endpoint.
            return jsonify({
                # Preenche o campo 'sucesso' do objeto ou resposta que está sendo montado.
                'sucesso': False,
                # Preenche o campo 'mensagem' do objeto ou resposta que está sendo montado.
                'mensagem': 'Não é possível excluir um usuário que possui empréstimos cadastrados.'
            # Fecha a estrutura da resposta e conclui o retorno HTTP.
            }), 409

        # Executa no banco a consulta SQL 'DELETE FROM USUARIO_PROJETO WHERE ID_USUARIO = ?'.
        cur.execute('DELETE FROM USUARIO_PROJETO WHERE ID_USUARIO = ?', (id_usuario,))
        # Executa no banco a consulta SQL 'DELETE FROM USUARIO WHERE ID_USUARIO = ?'.
        cur.execute('DELETE FROM USUARIO WHERE ID_USUARIO = ?', (id_usuario,))
        # Confirma definitivamente as alterações feitas na transação.
        con.commit()
        # Retorna uma resposta JSON de sucesso com status HTTP 200.
        return jsonify({'sucesso': True, 'mensagem': 'Usuário excluído com sucesso!'}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Desfaz as alterações da transação após uma falha.
        con.rollback()
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao excluir usuário: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/cadastro', methods=['POST'], associando a URL aos métodos HTTP informados.
@app.route('/cadastro', methods=['POST'])
# Define a função cadastro, que valida e cadastra um novo usuário.
def cadastro():
    # Verifica se o usuário autenticado é administrador.
    if not usuario_e_administrador():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Atribui a variável 'tipo' o resultado da expressão 'ler_inteiro(request.form.get('tipo', '0'))'.
        tipo = ler_inteiro(request.form.get('tipo', '0'))
        # Atribui a variável 'status' o resultado da expressão 'ler_inteiro(request.form.get('status', '0'))'.
        status = ler_inteiro(request.form.get('status', '0'))
        # Remove espaços extras das extremidades do texto.
        nome = request.form.get('nome', '').strip().lower()
        # Remove espaços extras das extremidades do texto.
        email = request.form.get('email', '').strip().lower()
        # Atribui a variável 'senha' o resultado da expressão 'request.form.get('senha')'.
        senha = request.form.get('senha')
        # Atribui a variável 'conf_senha' o resultado da expressão 'request.form.get('conf_senha')'.
        conf_senha = request.form.get('conf_senha')
        # Verifica se tipo not in (0, 1, 2).
        if tipo not in (0, 1, 2):
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': 'Perfil inválido.'}), 400
        # Verifica se status not in (0, 1).
        if status not in (0, 1):
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': 'Status inválido.'}), 400
        # Verifica se a condição nome é falsa.
        if not nome:
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': 'Nome é obrigatório.'}), 400
        # Verifica se a condição email or not senha é falsa.
        if not email or not senha:
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': 'E-mail e senha são obrigatórios.'}), 400
        # Verifica se senha != conf_senha.
        if senha != conf_senha:
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': 'As senhas não coincidem'}), 400

        # Atribui a variável 'erro_senha' o resultado da expressão 'verificar_senha(senha)'.
        erro_senha = verificar_senha(senha)
        # Verifica se a validação retornou uma mensagem de erro.
        if erro_senha:
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': erro_senha}), 400

        # Inicializa a lista 'projetos' vazia.
        projetos = []
        # Verifica se tipo == 2.
        if tipo == 2:
            # Percorre texto_id in request.form.getlist('projetos').
            for texto_id in request.form.getlist('projetos'):
                # Atribui a variável 'id_projeto' o resultado da expressão 'ler_inteiro(texto_id)'.
                id_projeto = ler_inteiro(texto_id)
                # Verifica se id_projeto is None.
                if id_projeto is None:
                    # Retorna uma resposta JSON de erro com status HTTP 400.
                    return jsonify({'sucesso': False, 'mensagem': 'Projeto inválido.'}), 400
                # Verifica se id_projeto not in projetos.
                if id_projeto not in projetos:
                    # Adiciona o item atual à lista acumulada.
                    projetos.append(id_projeto)
            # Percorre id_projeto in projetos.
            for id_projeto in projetos:
                # Executa no banco a consulta SQL 'SELECT ID_PROJETO FROM PROJETO WHERE ID_PROJETO = ?'.
                cur.execute('SELECT ID_PROJETO FROM PROJETO WHERE ID_PROJETO = ?', (id_projeto,))
                # Verifica se a condição cur.fetchone() é falsa.
                if not cur.fetchone():
                    # Retorna uma resposta JSON de erro com status HTTP 400.
                    return jsonify({'sucesso': False, 'mensagem': 'Projeto não encontrado.'}), 400

        # Executa no banco a consulta SQL 'SELECT EMAIL FROM USUARIO WHERE EMAIL = ?'.
        cur.execute('SELECT EMAIL FROM USUARIO WHERE EMAIL = ?', (email,))
        # Verifica se cur.fetchone().
        if cur.fetchone():
            # Retorna uma resposta JSON de erro com status HTTP 409.
            return jsonify({'sucesso': False, 'mensagem': 'E-mail já cadastrado'}), 409

        # Atribui a variável 'senha_hash' o resultado da expressão 'generate_password_hash(senha)'.
        senha_hash = generate_password_hash(senha)
        # Inicia a execução da consulta ou comando SQL no banco de dados.
        cur.execute('''
            INSERT INTO USUARIO(NOME, EMAIL, TIPO, SENHA_HASH, STATUS) -- Inicia a inclusão de um novo registro.
            VALUES(?, ?, ?, ?, ?) -- Define os valores que serão gravados.
            RETURNING ID_USUARIO -- Solicita ao banco o identificador gerado.
        ''', (nome.capitalize(), email, tipo, senha_hash, status))  # Fecha a string SQL usada pela consulta.
        # Obtém um valor do primeiro registro e o armazena em 'id_novo_usuario'.
        id_novo_usuario = cur.fetchone()[0]
        # Percorre id_projeto in projetos.
        for id_projeto in projetos:
            # Inicia a execução da consulta ou comando SQL no banco de dados.
            cur.execute('''
                INSERT INTO USUARIO_PROJETO(ID_USUARIO, ID_PROJETO) -- Inicia a inclusão de um novo registro.
                VALUES(?, ?) -- Define os valores que serão gravados.
            ''', (id_novo_usuario, id_projeto))  # Fecha a string SQL usada pela consulta.
        # Confirma definitivamente as alterações feitas na transação.
        con.commit()
        # Retorna uma resposta JSON de sucesso com status HTTP 201.
        return jsonify({'sucesso': True, 'mensagem': 'Usuário cadastrado com sucesso!'}), 201
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Desfaz as alterações da transação após uma falha.
        con.rollback()
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao criar usuário: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/login', methods=['POST'], associando a URL aos métodos HTTP informados.
@app.route('/login', methods=['POST'])
# Define a função login, que valida as credenciais e cria a sessão do usuário.
def login():
    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Converte os dados recebidos na requisição para um dicionário manipulável.
        dados = request.get_json()
        # Verifica se dados is None.
        if dados is None:
            # Converte os dados recebidos na requisição para um dicionário manipulável.
            dados = {}
        # Remove espaços extras das extremidades do texto.
        email = str(dados.get('email', '')).strip()
        # Atribui a variável 'senha' o resultado da expressão 'dados.get('senha')'.
        senha = dados.get('senha')
        # Verifica se a condição email or not senha é falsa.
        if not email or not senha:
            # Retorna uma resposta JSON de sucesso com status HTTP 400.
            return jsonify({'erro': 'Preencha todos os campos'}), 400

        # Inicia a execução da consulta ou comando SQL no banco de dados.
        cur.execute('''
            SELECT ID_USUARIO, NOME, SENHA_HASH, TIPO -- Inicia a seleção dos campos solicitados.
            FROM USUARIO -- Define a tabela USUARIO da consulta.
            WHERE LOWER(EMAIL) = LOWER(?) -- Filtra os registros conforme a condição informada.
        ''', (email,))  # Fecha a string SQL usada pela consulta.
        # Obtém um valor do primeiro registro e o armazena em 'usuario'.
        usuario = cur.fetchone()
        # Verifica se a condição usuario é falsa.
        if not usuario:
            # Retorna uma resposta JSON de sucesso com status HTTP 400.
            return jsonify({'erro': 'Email não cadastrado'}), 400
        # Verifica se a condição check_password_hash(usuario[2], senha) é falsa.
        if not check_password_hash(usuario[2], senha):
            # Retorna uma resposta JSON de erro com status HTTP 401.
            return jsonify({'sucesso': False, 'mensagem': 'Email ou senha está incorreta'}), 401

        # Atribui a variável 'token' o resultado da expressão 'gerar_token(usuario[0])'.
        token = gerar_token(usuario[0])
        # Remove espaços extras das extremidades do texto.
        nome = usuario[1].strip().split()[0]
        # Monta a estrutura JSON usada na resposta da API.
        resposta = make_response(jsonify({
            # Preenche o campo 'id_usuario' do objeto ou resposta que está sendo montado.
            'id_usuario': usuario[0],
            # Preenche o campo 'id_user' do objeto ou resposta que está sendo montado.
            'id_user': usuario[0],
            # Preenche o campo 'nome' do objeto ou resposta que está sendo montado.
            'nome': nome,
            # Preenche o campo 'tipo' do objeto ou resposta que está sendo montado.
            'tipo': usuario[3],
            # Preenche o campo 'token' do objeto ou resposta que está sendo montado.
            'token': token,
            # Preenche o campo 'sucesso' do objeto ou resposta que está sendo montado.
            'sucesso': True,
            # Preenche o campo 'mensagem' do objeto ou resposta que está sendo montado.
            'mensagem': 'Logado com sucesso!'
        # Fecha a estrutura da resposta e conclui o retorno HTTP.
        }), 200)
        # Inicia a configuração do cookie que manterá o token de autenticação.
        resposta.set_cookie(
            # Atribui a variável ''access_token', token, httponly' o resultado da expressão 'True, secure=False,'.
            'access_token', token, httponly=True, secure=False,
            # Atribui a variável 'samesite' o resultado da expressão ''Lax', path='/', max_age=3600'.
            samesite='Lax', path='/', max_age=3600
        # Fecha a chamada ou a lista de argumentos iniciada anteriormente.
        )
        # Retorna resposta.
        return resposta
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao login: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()
