# Histórico de alterações

O menu **Administração → Logs** consulta `HISTORICO` no BancoLog, por `GET /logs`.
Somente administradores (tipo 0) podem acessar a rota. A tela possui paginação,
filtros de data, tabela, ação, nome/e-mail e identificador do registro.

## Implantação

1. No backend, configure `DB_LOG_NAME` se o destino não for
   `/var/lib/firebird/data/BANCOLOG.FDB`. A consulta aceita também `DB_LOG_HOST`,
   `DB_LOG_USER` e `DB_LOG_PASSWORD`; quando omitidos utiliza os dados do banco principal.
2. Execute `python migrar_auditoria.py` **antes** de publicar a aplicação nova.
   O script faz backup lógico dos dois bancos no volume do Firebird, preserva as
   fontes anteriores das triggers em `auditoria-backups` no volume do backend e
   acrescenta as colunas de autoria sem apagar registros antigos.
   Ele deve ser executado no ambiente do Guadalupe, com as credenciais no ambiente.
3. Publique backend e frontend. Nenhuma credencial é enviada ao navegador.

As triggers do principal gravam no BancoLog usando a transação externa comum.
Inclusões são registradas em AFTER INSERT; alterações e exclusões em BEFORE.
As 13 tabelas originalmente auditadas continuam cobertas, e ARKHE_COBRANCA
também possui triggers. São 42 triggers no ambiente atual.
O script é idempotente para as triggers já migradas. A restauração de fontes antigas
deve utilizar o backup privado do servidor, pois as fontes contêm a autenticação EDS.

## Autoria

O servidor valida o token e consulta o nome no cadastro. O contexto `GLOG_*` é
aplicado à conexão legada no início de cada requisição e a novas conexões criadas
por `abrir_conexao`. O contexto é limpo ao finalizar a requisição. O cliente não
decide o autor por um campo `id_usuario` do formulário. Nome e ID são copiados
para o evento, preservando a identificação após renomeação/exclusão do usuário.

A conexão legada é compartilhada e o Waitress permanece com **uma thread**, como
já estava configurado. Antes de ampliar a concorrência, migre a conexão legada
para conexões por requisição; contextos de sessão não podem ser compartilhados
por requisições simultâneas. Tarefas sem sessão são identificadas como
“Sistema / acesso direto”; elas não são atribuídas ao último usuário conectado.

Registros antigos permanecem com a autoria original. Quando não possuem um nome
salvo, a interface informa que o autor não foi identificado. E-mail legado pode
indicar o usuário associado ao cadastro, sem comprovar o autor da mudança.
Senhas e hashes continuam fora do histórico.

## Verificação

`python -m unittest discover -s tests -p test_auditoria.py -v`

Testes cobrem permissão, filtros parametrizados, paginação, datas, falha do banco,
histórico legado e limpeza de autoria entre requisições. No Firebird de produção,
INSERT, UPDATE e DELETE foram executados em uma transação de teste revertida,
com confirmação de que os eventos de teste não permaneceram no BancoLog.
