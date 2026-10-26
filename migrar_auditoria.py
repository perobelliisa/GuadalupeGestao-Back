"""Amplia o BancoLog e as triggers existentes sem apagar histórico.

Execute no container do Guadalupe: python migrar_auditoria.py
As credenciais são lidas do ambiente; nunca são impressas ou versionadas.
"""
import json
import os
import re
from datetime import datetime
from pathlib import Path
import fdb
import fdb.services


def conectar(database):
    return fdb.connect(host=os.environ['DB_HOST'], database=database,
                       user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'], charset='UTF8')


def literal(texto):
    return "'" + texto.replace("'", "''") + "'"


def atualizar_trigger(nome, tabela, fonte, campos):
    acao = 'INSERT' if nome.startswith('TG_AI_') else 'UPDATE' if nome.startswith('TG_AU_') else 'DELETE'
    registro = 'OLD' if acao == 'DELETE' else 'NEW'
    ids = ['ID'] if 'ID' in campos else [c for c in campos if c.startswith('ID_')]
    # Prioriza a chave própria da tabela; em vínculos mantém a chave composta.
    propria = 'ID_' + tabela
    ids = [propria] if propria in ids else ids[:2]
    chave = " || '/' || ".join(f"COALESCE(CAST({registro}.{c} AS VARCHAR(100)), '')" for c in ids) or "''"
    declaracoes = '''DECLARE VARIABLE V_AUD_ID INTEGER;
DECLARE VARIABLE V_AUD_NOME VARCHAR(254);
DECLARE VARIABLE V_AUD_REGISTRO VARCHAR(254);
'''
    fonte = fonte.replace('AS\n', 'AS\n' + declaracoes, 1)
    if 'DECLARE VARIABLE V_AUD_ID' not in fonte:
        raise RuntimeError('Formato de trigger não reconhecido: ' + nome)
    bloco = f'''
    V_AUD_ID = CAST(RDB$GET_CONTEXT('USER_SESSION', 'GLOG_ID') AS INTEGER);
    V_AUD_NOME = COALESCE(RDB$GET_CONTEXT('USER_SESSION', 'GLOG_NOME'), 'Sistema / acesso direto');
    V_AUD_REGISTRO = {chave};
    V_EMAIL = COALESCE(RDB$GET_CONTEXT('USER_SESSION', 'GLOG_EMAIL'), 'NAO IDENTIFICADO');
'''
    # Substitui o destino antigo de desenvolvimento pelo arquivo persistente real.
    fonte = re.sub(r"ON EXTERNAL DATA SOURCE\s*'[^']*'", 'ON EXTERNAL DATA SOURCE\n    ' + literal(os.getenv('DB_LOG_SOURCE', 'localhost:/var/lib/firebird/data/BANCOLOG.FDB')), fonte, flags=re.I)
    fonte = re.sub(r"AS USER\s*'[^']*'\s*PASSWORD\s*'(?:[^']|'')*'", 'AS USER ' + literal(os.environ['DB_USER']) + '\n    PASSWORD ' + literal(os.environ['DB_PASSWORD']), fonte, flags=re.I)
    fonte = fonte.replace('    EXECUTE STATEMENT', bloco + '\n    EXECUTE STATEMENT', 1)
    fonte, colunas = re.subn(r'(INSERT INTO HISTORICO\s*\()\s*EMAIL,', r'\1 ID_USUARIO, NOME_USUARIO, REGISTRO_ID, EMAIL,', fonte, count=1, flags=re.I)
    fonte, valores = re.subn(r'VALUES\s*\(\?,\s*\?,\s*CURRENT_TIMESTAMP', 'VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP', fonte, count=1, flags=re.I)
    fonte, argumentos = re.subn(r'\(\s*:V_EMAIL,', '(:V_AUD_ID, :V_AUD_NOME, :V_AUD_REGISTRO, :V_EMAIL,', fonte, count=1)
    # Dispositivo do ator autenticado, e não o dispositivo salvo no registro editado.
    fonte = re.sub(r"(:V_EMAIL,\s*)(?:NEW\.DISPOSITIVO|OLD\.DISPOSITIVO|'NAO INFORMADO')", r"\1COALESCE(RDB$GET_CONTEXT('USER_SESSION', 'GLOG_DISPOSITIVO'), 'NAO INFORMADO')", fonte)
    if (colunas, valores, argumentos) != (1, 1, 1):
        raise RuntimeError('Não foi possível atualizar a trigger: ' + nome)
    momento = 'AFTER INSERT' if acao == 'INSERT' else 'BEFORE ' + acao
    return f'CREATE OR ALTER TRIGGER {nome} FOR {tabela} ACTIVE {momento} POSITION 100\n{fonte}'


def base_generica(campos, acao):
    def snapshot(prefixo):
        if not prefixo:
            return "''"
        partes = [f"COALESCE(CAST({prefixo}.{c} AS VARCHAR(500)), '')" for c in campos]
        return " || ' - ' || ".join(partes)
    antes = snapshot('OLD' if acao != 'INSERT' else None)
    depois = snapshot('NEW' if acao != 'DELETE' else None)
    return f'''AS
DECLARE VARIABLE V_EMAIL VARCHAR(254);
DECLARE VARIABLE V_ANTIGO VARCHAR(8191);
DECLARE VARIABLE V_NOVO VARCHAR(8191);
BEGIN
    V_ANTIGO = {antes};
    V_NOVO = {depois};
    EXECUTE STATEMENT ('INSERT INTO HISTORICO (EMAIL, DISPOSITIVO, DATA_HORA, TABELA, CAMPO, ACAO, CAMPO_ANTIGO, CAMPO_NOVO)
        VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)')
    (:V_EMAIL, 'NAO INFORMADO', 'ARKHE_COBRANCA', {literal(' - '.join(campos))}, {literal(acao)}, :V_ANTIGO, :V_NOVO)
    ON EXTERNAL DATA SOURCE 'localhost:/var/lib/firebird/data/BANCOLOG.FDB'
    AS USER 'SYSDBA' PASSWORD 'placeholder';
END'''


def executar():
    principal = conectar(os.environ['DB_NAME'])
    log = conectar(os.getenv('DB_LOG_NAME', '/var/lib/firebird/data/BANCOLOG.FDB'))
    try:
        # Backup lógico consistente dos dois bancos antes de qualquer DDL.
        instante = datetime.now().strftime('%Y%m%d_%H%M%S')
        servico = fdb.services.connect(host=os.environ['DB_HOST'], user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'])
        try:
            for nome, banco in [('principal', os.environ['DB_NAME']), ('historico', os.getenv('DB_LOG_NAME', '/var/lib/firebird/data/BANCOLOG.FDB'))]:
                destino_backup = '/var/lib/firebird/data/auditoria_' + nome + '_' + instante + '.fbk'
                servico.backup(banco, destino_backup)
                servico.wait()
                print('Backup lógico concluído:', nome)
        finally:
            servico.close()
        q = principal.cursor()
        q.execute("SELECT TRIM(RDB$TRIGGER_NAME), TRIM(RDB$RELATION_NAME), RDB$TRIGGER_SOURCE, RDB$TRIGGER_INACTIVE, RDB$TRIGGER_TYPE, RDB$TRIGGER_SEQUENCE FROM RDB$TRIGGERS WHERE COALESCE(RDB$SYSTEM_FLAG,0)=0")
        triggers = [dict(zip(['nome','tabela','fonte','inativa','tipo','posicao'], r)) for r in q.fetchall()]
        backup = Path(os.getenv('UPLOAD_FOLDER', '/data/guadalupe/arquivos')).parent / 'auditoria-backups'
        backup.mkdir(mode=0o700, parents=True, exist_ok=True)
        destino = backup / (datetime.now().strftime('%Y%m%d_%H%M%S') + '_triggers.json')
        destino.write_text(json.dumps(triggers, ensure_ascii=False, default=str))
        destino.chmod(0o600)
        cur = log.cursor()
        cur.execute("SELECT TRIM(RDB$FIELD_NAME) FROM RDB$RELATION_FIELDS WHERE RDB$RELATION_NAME='HISTORICO'")
        colunas = {r[0] for r in cur.fetchall()}
        for nome, tipo in [('ID_USUARIO','INTEGER'),('NOME_USUARIO','VARCHAR(254) CHARACTER SET UTF8'),('REGISTRO_ID','VARCHAR(254) CHARACTER SET UTF8')]:
            if nome not in colunas:
                cur.execute('ALTER TABLE HISTORICO ADD ' + nome + ' ' + tipo)
        log.commit()
        cur.execute("SELECT TRIM(RDB$INDEX_NAME) FROM RDB$INDICES WHERE RDB$RELATION_NAME='HISTORICO'")
        indices = {r[0] for r in cur.fetchall()}
        for nome, campo in [('IX_HIST_DATA','DATA_HORA'), ('IX_HIST_TABELA','TABELA')]:
            if nome not in indices:
                cur.execute(f'CREATE INDEX {nome} ON HISTORICO ({campo})')
        log.commit()
        q.execute("SELECT TRIM(RDB$RELATION_NAME), TRIM(RDB$FIELD_NAME) FROM RDB$RELATION_FIELDS ORDER BY RDB$FIELD_POSITION")
        tabelas = {}
        for tabela, campo in q.fetchall():
            tabelas.setdefault(tabela, []).append(campo)
        alteradas = 0
        for t in triggers:
            if not re.fullmatch(r'TG_A[IUD]_[A-Z_]+', t['nome']) or 'INSERT INTO HISTORICO' not in (t['fonte'] or '').upper():
                continue
            # Executar novamente não duplica colunas nem registros.
            if 'V_AUD_ID' in t['fonte']:
                continue
            q.execute(atualizar_trigger(t['nome'], t['tabela'], t['fonte'], tabelas[t['tabela']]))
            alteradas += 1
        for sigla, acao in [('AI','INSERT'),('AU','UPDATE'),('AD','DELETE')]:
            nome = 'TG_' + sigla + '_ARKHE_COBRANCA'
            if nome not in {t['nome'] for t in triggers}:
                campos = [c for c in tabelas['ARKHE_COBRANCA'] if c in ('ID','ID_COBRANCA','ID_USUARIO','ID_DOACAO','VALOR','SITUACAO','ID_PROJETO','DOADOR','CRIADO_EM','RECEBIDO_EM')]
                q.execute(atualizar_trigger(nome, 'ARKHE_COBRANCA', base_generica(campos, acao), tabelas['ARKHE_COBRANCA']))
                alteradas += 1
        principal.commit()
        print('Auditoria atualizada. Triggers:', alteradas, 'Histórico anterior preservado.')
    except Exception:
        principal.rollback()
        log.rollback()
        raise
    finally:
        principal.close()
        log.close()


if __name__ == '__main__':
    executar()
