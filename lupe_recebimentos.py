"""Acompanha cobranças autorizadas e guarda um agradecimento por conta/cobrança."""
from datetime import datetime, timezone
from decimal import Decimal
import json
from threading import Event, Thread
import time
from uuid import UUID, NAMESPACE_URL, uuid5

from historico_lupe import HistoricoLupe


def preparar_tabelas(con):
    con.execute('''CREATE TABLE IF NOT EXISTS lupe_pix_acompanhados (
        usuario TEXT NOT NULL, cobranca TEXT NOT NULL, conversa TEXT,
        proxima REAL NOT NULL DEFAULT 0, concluida INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (usuario, cobranca))''')
    con.execute('''CREATE TABLE IF NOT EXISTS lupe_avisos_pagamento (
        id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT NOT NULL,
        cobranca TEXT NOT NULL, conversa TEXT NOT NULL, texto TEXT NOT NULL,
        apos_mensagem INTEGER NOT NULL, criado_em TEXT NOT NULL,
        UNIQUE (usuario, cobranca))''')


def acompanhar_cobranca(con, usuario, cobranca, conversa=None):
    cobranca = str(UUID(str(cobranca)))
    preparar_tabelas(con)
    con.execute('''INSERT INTO lupe_pix_acompanhados (usuario,cobranca,conversa) VALUES (?,?,?)
        ON CONFLICT(usuario,cobranca) DO UPDATE SET conversa=COALESCE(excluded.conversa,lupe_pix_acompanhados.conversa)''', (str(usuario), cobranca, conversa))


class RecebimentosLupe:
    def __init__(self, consultar, banco=None, relogio=time.time, logger=None):
        self.consultar = consultar
        self.banco = banco or HistoricoLupe()
        self.relogio = relogio
        self.logger = logger
        self.parar = Event()
        self.thread = None

    def acompanhar(self, usuario, cobranca, conversa=None):
        with self.banco.conexao() as con:
            acompanhar_cobranca(con, usuario, cobranca, conversa)

    def recuperar_acoes(self):
        with self.banco.conexao() as con:
            preparar_tabelas(con)
            if not con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lupe_acoes'").fetchone(): return
            linhas = con.execute("SELECT a.usuario,a.conversa,a.plano FROM lupe_acoes a JOIN lupe_conversas c ON c.usuario=a.usuario AND c.id=a.conversa WHERE a.estado='concluida'").fetchall()
            for usuario, conversa, conteudo in linhas:
                plano = json.loads(conteudo)
                if plano.get('recurso') == 'pix_doacao' and plano.get('operacao') == 'gerar_pix':
                    acompanhar_cobranca(con, usuario, plano['dados']['id'], conversa)

    def reservar(self):
        with self.banco.conexao() as con:
            preparar_tabelas(con)
            con.execute('BEGIN IMMEDIATE')
            ids = [r[0] for r in con.execute('SELECT cobranca FROM lupe_pix_acompanhados WHERE concluida=0 AND proxima<=? GROUP BY cobranca ORDER BY MIN(proxima) LIMIT 10', (self.relogio(),)).fetchall()]
            for identificador in ids:
                con.execute('UPDATE lupe_pix_acompanhados SET proxima=? WHERE cobranca=? AND concluida=0', (self.relogio()+180, identificador))
            return ids

    def reagendar(self, identificador, segundos):
        with self.banco.conexao() as con:
            con.execute('UPDATE lupe_pix_acompanhados SET proxima=? WHERE cobranca=? AND concluida=0', (self.relogio()+segundos, identificador))

    def notificar(self, cobranca):
        if cobranca.get('situacao') != 'pago' or not cobranca.get('id_doacao'):
            raise ValueError('O recebimento ainda não foi confirmado e registrado.')
        valor = Decimal(str(cobranca.get('valor')))
        if not valor.is_finite() or valor <= 0:
            raise ValueError('O recebimento não informou um valor válido.')
        identificador = str(UUID(cobranca['id']))
        dinheiro = f'{valor:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')
        doador = str(cobranca.get('doador') or 'um doador').strip()
        texto = f'Recebemos R$ {dinheiro} da doação de {doador}. Muito obrigado pela contribuição! 💙'
        agora = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        with self.banco.conexao() as con:
            preparar_tabelas(con)
            con.execute('BEGIN IMMEDIATE')
            vinculos = con.execute('SELECT usuario,conversa FROM lupe_pix_acompanhados WHERE cobranca=? AND concluida=0', (identificador,)).fetchall()
            for usuario, conversa_id in vinculos:
                conversa_id = conversa_id or str(uuid5(NAMESPACE_URL, 'guadalupe:recebimentos:'+usuario))
                linha = con.execute('SELECT conteudo FROM lupe_conversas WHERE usuario=? AND id=?', (usuario, conversa_id)).fetchone()
                if linha:
                    conversa = self.banco.apresentar(con, usuario, json.loads(linha[0]))
                    conversa.pop('avisos', None)
                    conversa.pop('revisaoAvisos', None)
                else:
                    conversa = {'id':conversa_id,'criadaEm':agora,'atualizadaEm':agora,'mensagens':[],'revisao':1,'titulo':'Recebimentos de doações','resumo':texto,'quantidadeMensagens':0}
                cursor = con.execute('INSERT OR IGNORE INTO lupe_avisos_pagamento (usuario,cobranca,conversa,texto,apos_mensagem,criado_em) VALUES (?,?,?,?,?,?)', (usuario, identificador, conversa_id, texto, len(conversa['mensagens']), agora))
                if cursor.rowcount:
                    conversa.update(atualizadaEm=agora, resumo=texto)
                    con.execute('INSERT OR REPLACE INTO lupe_conversas VALUES (?,?,?,?,?)', (usuario, conversa_id, json.dumps(conversa, ensure_ascii=False), agora, conversa['revisao']))
                con.execute('UPDATE lupe_pix_acompanhados SET concluida=1 WHERE usuario=? AND cobranca=?', (usuario,identificador))

    def processar(self):
        for identificador in self.reservar():
            try:
                cobranca = self.consultar(identificador)
                if cobranca.get('id') != identificador: raise ValueError('Cobrança diferente da solicitada.')
                if cobranca.get('situacao') == 'pago': self.notificar(cobranca)
                else: self.reagendar(identificador, 5)
            except Exception:
                self.reagendar(identificador, 60)
                if self.logger: self.logger.warning('Não foi possível acompanhar um recebimento da Lupe; será consultado novamente.')

    def iniciar(self):
        if self.thread and self.thread.is_alive(): return
        def executar():
            recuperado = False
            while not self.parar.is_set():
                try:
                    if not recuperado:
                        self.recuperar_acoes()
                        recuperado = True
                    self.processar()
                except Exception:
                    if self.logger: self.logger.warning('Acompanhamento de recebimentos temporariamente indisponível.')
                self.parar.wait(5)
        self.thread = Thread(target=executar, name='lupe-recebimentos', daemon=True)
        self.thread.start()
