import datetime
import os
import uuid

from flask import jsonify, request
from werkzeug.utils import secure_filename

from main import app, con
from function import EXTENSOES_PERMITIDAS, id_usuario_logado


def garantir_tabelas_documentos():
    cur = con.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM RDB$RELATIONS WHERE RDB$RELATION_NAME = 'DOCUMENTO'")
        if cur.fetchone()[0] == 0:
            cur.execute('''
                CREATE TABLE DOCUMENTO (
                    ID_DOCUMENTO INTEGER NOT NULL PRIMARY KEY,
                    ID_USUARIO INTEGER,
                    NOME VARCHAR(255) NOT NULL,
                    CAMINHO VARCHAR(500) NOT NULL,
                    DATA_ENVIO TIMESTAMP NOT NULL
                )
            ''')
            con.commit()

        cur.execute("SELECT COUNT(*) FROM RDB$RELATIONS WHERE RDB$RELATION_NAME = 'DOCUMENTO_PROJETO'")
        if cur.fetchone()[0] == 0:
            cur.execute('''
                CREATE TABLE DOCUMENTO_PROJETO (
                    ID_DOCUMENTO INTEGER NOT NULL,
                    ID_PROJETO INTEGER NOT NULL,
                    PRIMARY KEY (ID_DOCUMENTO, ID_PROJETO)
                )
            ''')
            con.commit()
    finally:
        cur.close()


garantir_tabelas_documentos()


@app.route('/documentos', methods=['GET'])
def listar_documentos():
    if not id_usuario_logado():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 401

    cur = con.cursor()
    try:
        cur.execute('''
            SELECT D.ID_DOCUMENTO, D.NOME, D.CAMINHO, D.DATA_ENVIO,
                   DP.ID_PROJETO
            FROM DOCUMENTO D
            LEFT JOIN DOCUMENTO_PROJETO DP ON DP.ID_DOCUMENTO = D.ID_DOCUMENTO
            ORDER BY D.DATA_ENVIO DESC, D.ID_DOCUMENTO DESC
        ''')
        documentos = {}
        for item in cur.fetchall():
            identificador = item[0]
            if identificador not in documentos:
                documentos[identificador] = {
                    'id_documento': identificador,
                    'nome': str(item[1]).strip(),
                    'caminho': str(item[2]).strip(),
                    'data': item[3].isoformat() if item[3] else None,
                    'projetos': []
                }
            if item[4] is not None:
                documentos[identificador]['projetos'].append(item[4])
        return jsonify({'sucesso': True, 'documentos': list(documentos.values())}), 200
    except Exception as erro:
        return jsonify({'sucesso': False, 'erro': f'Erro ao listar documentos: {erro}'}), 500
    finally:
        cur.close()


@app.route('/documentos', methods=['POST'])
def cadastrar_documento():
    id_usuario = id_usuario_logado()
    if not id_usuario:
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 401

    arquivo = request.files.get('arquivo')
    if not arquivo or not arquivo.filename:
        return jsonify({'sucesso': False, 'mensagem': 'Selecione um arquivo para enviar.'}), 400

    titulo = str(request.form.get('titulo', '')).strip()
    if not titulo:
        return jsonify({'sucesso': False, 'mensagem': 'Informe o título do documento.'}), 400
    if len(titulo) > 255:
        return jsonify({'sucesso': False, 'mensagem': 'O título deve ter no máximo 255 caracteres.'}), 400

    nome_original = secure_filename(arquivo.filename)
    extensao = os.path.splitext(nome_original)[1].lower()
    if extensao not in EXTENSOES_PERMITIDAS:
        return jsonify({'sucesso': False, 'mensagem': 'Envie um arquivo PDF, JPG ou PNG.'}), 400

    ids_recebidos = request.form.getlist('projetos')
    if not ids_recebidos and request.form.get('id_projeto'):
        ids_recebidos = [request.form.get('id_projeto')]
    try:
        ids_projetos = list(dict.fromkeys(int(item) for item in ids_recebidos))
    except (TypeError, ValueError):
        return jsonify({'sucesso': False, 'mensagem': 'Projeto inválido.'}), 400
    if not ids_projetos:
        return jsonify({'sucesso': False, 'mensagem': 'Marque ao menos um projeto.'}), 400

    cur = con.cursor()
    caminho_fisico = None
    try:
        marcadores = ','.join('?' for _ in ids_projetos)
        cur.execute(f'SELECT ID_PROJETO FROM PROJETO WHERE ID_PROJETO IN ({marcadores})', ids_projetos)
        projetos_existentes = {item[0] for item in cur.fetchall()}
        if projetos_existentes != set(ids_projetos):
            return jsonify({'sucesso': False, 'mensagem': 'Um dos projetos selecionados não existe.'}), 400

        cur.execute('SELECT COALESCE(MAX(ID_DOCUMENTO), 0) + 1 FROM DOCUMENTO')
        id_documento = cur.fetchone()[0]
        pasta = os.path.join(app.config['UPLOAD_FOLDER'], 'documentos')
        os.makedirs(pasta, exist_ok=True)
        nome_salvo = f'documento_{id_documento}_{uuid.uuid4().hex[:10]}{extensao}'
        caminho_fisico = os.path.join(pasta, nome_salvo)
        caminho_publico = f'/arquivos/documentos/{nome_salvo}'
        arquivo.save(caminho_fisico)

        agora = datetime.datetime.now()
        cur.execute('''
            INSERT INTO DOCUMENTO (ID_DOCUMENTO, ID_USUARIO, NOME, CAMINHO, DATA_ENVIO)
            VALUES (?, ?, ?, ?, ?)
        ''', (id_documento, id_usuario, titulo, caminho_publico, agora))
        for id_projeto in ids_projetos:
            cur.execute('INSERT INTO DOCUMENTO_PROJETO (ID_DOCUMENTO, ID_PROJETO) VALUES (?, ?)',
                        (id_documento, id_projeto))
        con.commit()
        return jsonify({
            'sucesso': True,
            'mensagem': 'Documento enviado com sucesso.',
            'documento': {
                'id_documento': id_documento,
                'nome': titulo,
                'caminho': caminho_publico,
                'data': agora.isoformat(),
                'projetos': ids_projetos
            }
        }), 201
    except Exception as erro:
        con.rollback()
        if caminho_fisico and os.path.exists(caminho_fisico):
            os.remove(caminho_fisico)
        return jsonify({'sucesso': False, 'erro': f'Erro ao enviar documento: {erro}'}), 500
    finally:
        cur.close()


@app.route('/documentos/<int:id_documento>', methods=['DELETE'])
def excluir_documento(id_documento):
    if not id_usuario_logado():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 401

    cur = con.cursor()
    try:
        cur.execute('SELECT CAMINHO FROM DOCUMENTO WHERE ID_DOCUMENTO = ?', (id_documento,))
        registro = cur.fetchone()
        if not registro:
            return jsonify({'sucesso': False, 'mensagem': 'Documento não encontrado.'}), 404

        caminho_publico = str(registro[0]).strip()
        cur.execute('DELETE FROM DOCUMENTO_PROJETO WHERE ID_DOCUMENTO = ?', (id_documento,))
        cur.execute('DELETE FROM DOCUMENTO WHERE ID_DOCUMENTO = ?', (id_documento,))
        con.commit()

        prefixo = '/arquivos/'
        if caminho_publico.startswith(prefixo):
            caminho_relativo = caminho_publico[len(prefixo):].replace('/', os.sep)
            caminho_fisico = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], caminho_relativo))
            pasta_upload = os.path.abspath(app.config['UPLOAD_FOLDER'])
            if os.path.commonpath([pasta_upload, caminho_fisico]) == pasta_upload and os.path.isfile(caminho_fisico):
                os.remove(caminho_fisico)

        return jsonify({'sucesso': True, 'mensagem': 'Documento excluído com sucesso.'}), 200
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao excluir documento: {erro}'}), 500
    finally:
        cur.close()
