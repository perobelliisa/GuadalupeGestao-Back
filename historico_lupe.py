"""Histórico compartilhado da Lupe, com isolamento por conta e revisão otimista."""
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
import json
import os
from pathlib import Path
import re
import sqlite3

from flask import jsonify, request


class ErroHistorico(Exception):
    def __init__(self, mensagem, status):
        super().__init__(mensagem)
        self.status = status


def validar_id(identificador):
    if not isinstance(identificador, str) or not re.fullmatch(r'[a-z0-9-]{1,100}', identificador):
        raise ErroHistorico('A conversa selecionada é inválida.', 400)


def validar_conversa(dados, identificador):
    validar_id(identificador)
    if not isinstance(dados, dict) or dados.get('id') != identificador:
        raise ErroHistorico('Envie uma conversa válida.', 400)
    mensagens = dados.get('mensagens')
    if not isinstance(mensagens, list) or not mensagens or len(mensagens) % 2 or len(mensagens) > 2000:
        raise ErroHistorico('Envie uma conversa completa com a Lupe.', 400)
    limpas = []
    for i, mensagem in enumerate(mensagens):
        papel = 'lupe' if i % 2 else 'usuario'
        if not isinstance(mensagem, dict) or mensagem.get('papel') != papel:
            raise ErroHistorico('Envie uma conversa válida.', 400)
        texto = mensagem.get('texto')
        if not isinstance(texto, str) or not texto.strip() or len(texto) > (8000 if i % 2 else 2000):
            raise ErroHistorico('Sua mensagem excede o tamanho permitido ou está vazia.', 400)
        limpas.append({'papel': papel, 'texto': texto})
    if type(dados.get('revisao', 0)) is not int or dados.get('revisao', 0) < 0:
        raise ErroHistorico('A revisão da conversa é inválida.', 400)
    for campo in ('criadaEm', 'atualizadaEm'):
        try:
            data = datetime.fromisoformat(dados[campo].replace('Z', '+00:00'))
            if data.tzinfo is None:
                raise ValueError()
        except (KeyError, ValueError, TypeError, AttributeError):
            raise ErroHistorico('A data da conversa é inválida.', 400) from None
    return {**dados, 'mensagens': limpas}


def metadados(conversa):
    return {**{campo: conversa[campo] for campo in ('id', 'titulo', 'resumo', 'atualizadaEm', 'quantidadeMensagens', 'revisao')}, 'revisaoAvisos': conversa.get('revisaoAvisos', 0)}


class HistoricoLupe:
    def __init__(self, caminho=None):
        self.caminho = Path(caminho or os.environ.get('LUPE_DB_PATH') or Path(__file__).with_name('dados') / 'lupe.sqlite3')

    @contextmanager
    def conexao(self):
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.caminho, timeout=10)
        try:
            con.execute('PRAGMA journal_mode=WAL')
            con.execute('''CREATE TABLE IF NOT EXISTS lupe_conversas (
                usuario TEXT NOT NULL, id TEXT NOT NULL, conteudo TEXT NOT NULL,
                atualizada_em TEXT NOT NULL, revisao INTEGER NOT NULL,
                PRIMARY KEY (usuario, id))''')
            con.commit()
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def listar(self, usuario):
        with self.conexao() as con:
            linhas = con.execute('SELECT conteudo FROM lupe_conversas WHERE usuario=? ORDER BY atualizada_em DESC', (str(usuario),)).fetchall()
            return [metadados(self.apresentar(con, usuario, json.loads(linha[0]))) for linha in linhas]

    def carregar(self, usuario, identificador):
        validar_id(identificador)
        with self.conexao() as con:
            linha = con.execute('SELECT conteudo FROM lupe_conversas WHERE usuario=? AND id=?', (str(usuario), identificador)).fetchone()
            if linha:
                return self.apresentar(con, usuario, json.loads(linha[0]))
        if not linha:
            raise ErroHistorico('Esta conversa não está mais disponível.', 404)

    def apresentar(self, con, usuario, conversa):
        # Oculta pares artificiais antigos somente quando correspondem à auditoria
        # da própria conta. Mensagens escritas livremente não são removidas.
        if not con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lupe_acoes'").fetchone():
            return self.com_avisos(con, usuario, conversa)
        linhas = con.execute('SELECT plano,resultado,estado FROM lupe_acoes WHERE usuario=? AND conversa=? AND resultado IS NOT NULL', (str(usuario), conversa['id'])).fetchall()
        artificiais = {}
        for plano, resultado, estado in linhas:
            titulo = json.loads(plano)['titulo']
            for prefixo in ('Confirmar: ', 'Cancelar: '):
                artificiais[(prefixo + titulo, resultado)] = estado
        mensagens = []
        originais = conversa['mensagens']
        for i in range(0, len(originais), 2):
            par = originais[i:i+2]
            estado = artificiais.get((par[0]['texto'], par[1]['texto'])) if len(par) == 2 else None
            if estado:
                if mensagens and mensagens[-1]['texto'].startswith('Preparei a proposta. Confira os dados abaixo'):
                    texto = par[1]['texto'] if estado == 'concluida' else 'Vamos conferir os dados para continuar.'
                    mensagens[-1] = {'papel': 'lupe', 'texto': texto}
                continue
            mensagens.extend(par)
        if mensagens:
            conversa = {**conversa, 'mensagens': mensagens, 'quantidadeMensagens': len(mensagens), 'resumo': ' '.join(mensagens[-1]['texto'].replace('**', '').split())[:140]}
        return self.com_avisos(con, usuario, conversa)

    def com_avisos(self, con, usuario, conversa):
        if not con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lupe_avisos_pagamento'").fetchone():
            return conversa
        linhas = con.execute('SELECT id,texto,apos_mensagem,criado_em FROM lupe_avisos_pagamento WHERE usuario=? AND conversa=? ORDER BY id', (str(usuario),conversa['id'])).fetchall()
        avisos = [{'id':str(r[0]),'texto':r[1],'aposMensagem':r[2],'criadoEm':r[3]} for r in linhas]
        conversa = {**conversa, 'avisos':avisos, 'revisaoAvisos':linhas[-1][0] if linhas else 0, 'quantidadeMensagens':len(conversa['mensagens'])+len(avisos)}
        if avisos and avisos[-1]['criadoEm'] >= conversa['atualizadaEm']:
            conversa['resumo'] = ' '.join(avisos[-1]['texto'].split())[:140]
        return conversa

    def responder_acao(self, con, usuario, identificador, plano, texto):
        linha = con.execute('SELECT conteudo FROM lupe_conversas WHERE usuario=? AND id=?', (str(usuario), identificador)).fetchone()
        if not linha:
            return
        conversa = self.apresentar(con, usuario, json.loads(linha[0]))
        mensagens = conversa['mensagens']
        for i in range(len(mensagens)-1, 0, -2):
            correspondente = mensagens[i]['texto'] == plano.get('mensagem_proposta') and mensagens[i-1]['texto'].strip() == plano.get('mensagem_usuario')
            anterior = not plano.get('mensagem_proposta') and mensagens[i]['texto'] == 'Preparei a proposta. Confira os dados abaixo e escolha Confirmar ou Cancelar. Nenhuma alteração foi realizada ainda.'
            if correspondente or anterior:
                mensagens[i] = {'papel': 'lupe', 'texto': texto}
                break
        else:
            return  # Uma resposta modificada em outro dispositivo não é sobrescrita.
        agora = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        conversa.update(atualizadaEm=agora, revisao=conversa['revisao']+1, quantidadeMensagens=len(mensagens), resumo=' '.join(mensagens[-1]['texto'].replace('**', '').split())[:140])
        con.execute('UPDATE lupe_conversas SET conteudo=?,atualizada_em=?,revisao=? WHERE usuario=? AND id=?', (json.dumps(conversa, ensure_ascii=False), agora, conversa['revisao'], str(usuario), identificador))

    def salvar(self, usuario, identificador, dados):
        dados = validar_conversa(dados, identificador)
        with self.conexao() as con:
            con.execute('BEGIN IMMEDIATE')
            linha = con.execute('SELECT conteudo FROM lupe_conversas WHERE usuario=? AND id=?', (str(usuario), identificador)).fetchone()
            atual = json.loads(linha[0]) if linha else None
            if atual:
                if atual['mensagens'] == dados['mensagens']:
                    return self.apresentar(con, usuario, atual)  # Repetição não duplica a conversa.
                if dados.get('importacao') is True and atual['mensagens'][:len(dados['mensagens'])] == dados['mensagens']:
                    return self.apresentar(con, usuario, atual)
                if dados.get('revisao', 0) != atual['revisao']:
                    raise ErroHistorico('A conversa foi atualizada em outro dispositivo. Reabra o histórico ou salve esta resposta como uma nova conversa.', 409)
            elif dados.get('revisao', 0) != 0:
                raise ErroHistorico('Esta conversa foi excluída em outro dispositivo. Salve como uma nova conversa para preservar suas mensagens.', 409)
            agora = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
            conversa = {
                'id': identificador, 'criadaEm': atual['criadaEm'] if atual else dados['criadaEm'],
                'atualizadaEm': dados['atualizadaEm'] if not atual and dados.get('importacao') is True else agora,
                'mensagens': dados['mensagens'], 'revisao': atual['revisao'] + 1 if atual else 1,
                'titulo': ' '.join(dados['mensagens'][0]['texto'].split())[:80],
                'resumo': ' '.join(dados['mensagens'][-1]['texto'].replace('**', '').split())[:140],
                'quantidadeMensagens': len(dados['mensagens']),
            }
            con.execute('INSERT OR REPLACE INTO lupe_conversas VALUES (?, ?, ?, ?, ?)',
                        (str(usuario), identificador, json.dumps(conversa, ensure_ascii=False), conversa['atualizadaEm'], conversa['revisao']))
        return self.carregar(usuario, identificador)

    def excluir(self, usuario, identificador):
        validar_id(identificador)
        with self.conexao() as con:
            con.execute('DELETE FROM lupe_conversas WHERE usuario=? AND id=?', (str(usuario), identificador))
            if con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lupe_pix_acompanhados'").fetchone():
                con.execute('UPDATE lupe_pix_acompanhados SET concluida=1 WHERE usuario=? AND conversa=?', (str(usuario), identificador))
                con.execute('DELETE FROM lupe_avisos_pagamento WHERE usuario=? AND conversa=?', (str(usuario), identificador))
            if con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lupe_acoes'").fetchone():
                con.execute("UPDATE lupe_acoes SET estado='cancelada',resultado='Conversa excluída. Ação cancelada.' WHERE usuario=? AND conversa=? AND estado='preparada'", (str(usuario), identificador))


def registrar_historico_lupe(app, autorizado, identificar_usuario, repositorio=None):
    repositorio = repositorio or HistoricoLupe()

    def proteger(funcao):
        @wraps(funcao)
        def executar(*args, **kwargs):
            usuario = identificar_usuario()
            if not usuario or not autorizado() or request.headers.get('X-Lupe-Usuario', str(usuario)) != str(usuario):
                return jsonify(sucesso=False, mensagem='Acesso não autorizado.'), 403
            try:
                return funcao(usuario, *args, **kwargs)
            except ErroHistorico as erro:
                return jsonify(sucesso=False, mensagem=str(erro)), erro.status
            except (sqlite3.Error, OSError):
                app.logger.error('Falha de armazenamento no histórico da Lupe')
                return jsonify(sucesso=False, mensagem='Não foi possível acessar o histórico da Lupe. Tente novamente.'), 503
        return executar

    @app.route('/lupe/conversas', methods=['GET'])
    @proteger
    def listar_conversas_lupe(usuario):
        return jsonify(sucesso=True, conversas=repositorio.listar(usuario))

    @app.route('/lupe/conversas/<identificador>', methods=['GET', 'PUT', 'DELETE'])
    @proteger
    def conversa_lupe(usuario, identificador):
        if request.method == 'GET':
            return jsonify(sucesso=True, conversa=repositorio.carregar(usuario, identificador))
        if request.method == 'DELETE':
            repositorio.excluir(usuario, identificador)
            return jsonify(sucesso=True, conversas=repositorio.listar(usuario))
        if request.content_length and request.content_length > 4 * 1024 * 1024:
            return jsonify(sucesso=False, mensagem='Sua conversa excede o tamanho permitido.'), 413
        conversa = repositorio.salvar(usuario, identificador, request.get_json(silent=True))
        return jsonify(sucesso=True, conversa=conversa, conversas=repositorio.listar(usuario))
