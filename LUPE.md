# Lupe e histórico compartilhado

## Comandos e confirmação

`POST /lupe/chat` recebe `mensagens` e `conversa_id` e retorna `resposta` e `acoes`.
`main.py` registra a Lupe com a função `id_usuario_logado`. `lupe_agente.py` oferece
ao Gemini somente duas ferramentas: `consultar_sistema` e `preparar_acao`.
O modelo não recebe ferramentas para executar ou confirmar escritas.

Consultas: receitas, despesas, livro-caixa, doações, empréstimos, categorias,
projetos, pendências, documentos e usuários. Totais são calculados sobre todos
os registros filtrados antes da paginação de até 50 itens.

Escritas disponíveis: criar receitas, despesas, doações e empréstimos; alterar
esses recursos, categorias e usuários; excluir os quatro primeiros, documentos
e usuários; registrar pagamentos de despesas e ocorrências de pendências.
Categoria nova é criada pela rota de lançamento existente. Cadastro de usuário
ou projeto, upload e transferência bancária não são ferramentas do agente.

`lupe_acoes.py` encaminha as operações às rotas autorizadas existentes, mantendo
os cookies/Bearer somente no servidor. Campos e caminhos são limitados; senhas
e tokens não integram as consultas. Validações e permissões existentes continuam
valendo, inclusive ao confirmar. Editar preserva os campos não solicitados.

- `GET /lupe/acoes?conversa_id=<id>`: propostas e resultados da própria conta.
- `POST /lupe/acoes/<id>/confirmar`: exige exatamente `{"confirmar": true}`.
- `POST /lupe/acoes/<id>/cancelar`: cancela sem executar a operação.

As propostas duram 15 minutos e ficam na tabela `lupe_acoes` do mesmo SQLite do
histórico. Uma nova proposta substitui a pendente da mesma conversa; excluir a
conversa cancela propostas pendentes. Os clientes exibem uma prévia antes dos
botões de confirmação e sincronizam os estados automaticamente.

A interface exibe somente a proposta pendente mais recente. Confirmar ou cancelar
atualiza a resposta original da Lupe no servidor, com revisão otimista preservada,
sem inserir mensagens artificiais de “Confirmar:”/“Cancelar:”. Essa atualização
usa a mesma transação SQLite que grava o resultado da ação. Uma resposta que já
foi editada em outro dispositivo não é sobrescrita.
Falhas ficam na auditoria das ações e chegam à interface como aviso temporário;
não são acrescentadas ao conteúdo da conversa. Pares artificiais de versões
anteriores são ocultados na leitura quando correspondem à auditoria da conta.

Doação para a missão não exige projeto: ausência, `null` ou `0` em `id_projeto`
é normalizada para `null`. A prévia mostra “Missão Guadalupe”. A data é validada
antes de apresentar a confirmação, seguindo a regra existente do cadastro.

A confirmação registra `executando` numa transação SQLite antes de chamar a
rota de negócio, impedindo execução duplicada em cliques ou requisições concorrentes.
Alterações no registro após a proposta invalidam a execução. Não existe transação
distribuída entre SQLite e Firebird: falha após iniciar a escrita pode deixar o
resultado `incerta` ou `executando`. Confira o cadastro antes de propor novamente;
essas ações nunca são repetidas automaticamente. Confirmações concluídas ou
canceladas retornam o resultado salvo, sem nova escrita.

Verificação no projeto mobile: `python tests/lupe_agente_backend.py` testa rotas
Flask simuladas e SQLite temporário, sem operações no banco financeiro real.

## Pagamentos e códigos de doação

`lupe_pagamentos.py` acrescenta duas ferramentas ao agente:

- `consultar_pagamentos`: despesas (situação e forma de pagamento), empréstimos
  (parcelas pagas e quitação) e cobranças de doação da Arkhé. Permite filtros por
  período, busca, projeto/missão, situação e paginação. Totais são calculados
  sobre todos os registros filtrados; valores livres não definidos são contados
  separadamente. O valor de um empréstimo é o principal, não a soma paga.
- `preparar_pix_doacao`: prepara uma proposta com doador, valor fixo ou livre,
  destino e conta recebedora. Não gera código antes da confirmação explícita.

O código é gerado pela integração Arkhé existente, para pagamento dentro da Arkhé.
Não é um Pix bancário interoperável gerado localmente. O agente não pode escolher
uma chave ou conta recebedora: a conta vem de `GET /integracoes/arkhe/conta` e é
conferida novamente ao confirmar. Projeto é opcional; a missão usa vínculo vazio.
Não é exigida data contábil para criar uma cobrança ainda não recebida.

Após confirmar, `POST /integracoes/arkhe/cobrancas` recebe um UUID gerado pelo
servidor e preservado na proposta. A idempotência da integração e da Lupe impede
duplicar a cobrança. O código retornado pelo provedor é copiado exatamente para
a resposta original da Lupe e fica disponível no histórico mobile/desktop.
A geração não confirma pagamento nem cria doação/entrada financeira.

O novo `GET /integracoes/arkhe/cobrancas/<uuid>/status` confere o pagamento no
provedor sem alterar cobrança, doação ou livro-caixa. Retorna a situação bancária,
a situação registrada localmente, `recebimento_registrado` e a fonte da consulta.
Sem atualização, a ferramenta informa que consultou os dados locais. Para obter
o código novamente, a ferramenta identifica a cobrança e confere seu status;
códigos já pagos não são apresentados para novo pagamento. O endpoint `POST
/integracoes/arkhe/cobrancas/<uuid>/consultar` existente continua sendo a operação
que confirma e registra o recebimento no financeiro.

Configure `ARKHE_CLIENT_ID` e `ARKHE_CLIENT_SECRET` no ambiente do backend, ou
em `arkhe.local.json`, conforme o README da API. As credenciais nunca vão para o
aplicativo ou modelo. Reinicie o backend após instalar estes módulos. Sem essa
configuração, a Lupe explica que o administrador precisa ativar a integração.

Validação sem banco/conta reais: `python -B tests/lupe_pagamentos_backend.py` no
mobile e `python -B -m unittest discover -s tests -p test_arkhe.py` no backend.

## Histórico compartilhado

## Agradecimento automático de pagamentos

`lupe_recebimentos.py` acompanha em segundo plano as cobranças criadas na Lupe
e as cobranças pendentes que uma conta autorizada criou ou consultou em Doações.
O acompanhamento inicia ao executar `main.py` e consulta a Arkhé a cada ciclo
de cinco segundos, agrupando consultas da mesma cobrança e adiando falhas de rede.
O backend precisa permanecer em execução. A geração não envia agradecimento.

O serviço reutiliza a confirmação de recebimento da integração: verifica a
resposta bancária e registra a doação/livro-caixa antes de publicar o aviso.
Uma falha no registro financeiro não gera uma mensagem falsa de recebimento.
Cada conta recebe um único agradecimento por cobrança, persistido no SQLite;
reiniciar ou consultar simultaneamente não repete a mensagem.

Na Lupe, o aviso entra na conversa que gerou o código. Para cobranças da tela de
Doações, é criada a conversa “Recebimentos de doações” na conta que as acompanhou.
São mensagens internas do chat; não são enviadas por WhatsApp ou e-mail.
Os avisos usam o campo `avisos` e o marcador `revisaoAvisos`, separados dos pares
de mensagens digitadas. Assim não há mensagem falsa de usuário nem conflito de
edição causado apenas pela chegada de um pagamento. Os clientes inserem o aviso
na posição da conversa em que ele chegou e sincronizam sem recarregar a página.

Exemplo: “Recebemos R$ 50,00 da doação de Ana. Muito obrigado pela contribuição! 💙”.

Verificação sem pagamentos reais: `python -B tests/lupe_recebimentos_backend.py`
e `node --test tests/mensagensLupe.test.cjs` no projeto mobile.

A Lupe atende pelo `POST /lupe/chat`, usando a configuração do Gemini existente.
O histórico é compartilhado entre mobile e desktop pelo backend:

- `GET /lupe/conversas`: lista as conversas da conta autenticada.
- `GET /lupe/conversas/<id>`: recupera uma conversa.
- `PUT /lupe/conversas/<id>`: cria ou atualiza o conteúdo com revisão otimista.
- `DELETE /lupe/conversas/<id>`: exclui uma conversa da conta.

Reinicie `main.py` após a atualização. O módulo `historico_lupe.py` cria automaticamente
`dados/lupe.sqlite3` na primeira consulta. O histórico usa SQLite, separado dos registros
financeiros do Firebird. O arquivo é ignorado pelo Git e deve ser incluído nos backups.
Em hospedagem, configure `LUPE_DB_PATH` para um arquivo em volume persistente.
Todas as instâncias do aplicativo devem usar o mesmo backend e a mesma base de histórico.

O usuário vem exclusivamente da sessão autenticada (cookie `access_token` ou Bearer).
O campo `X-Lupe-Usuario`, quando presente, é conferido contra a sessão para impedir
que uma resposta pendente de uma sessão antiga seja salva em outra conta após logout.

Cada atualização envia `id`, `criadaEm`, `atualizadaEm`, `mensagens` e `revisao`.
O servidor devolve `conversa` e `conversas` com a nova revisão. Atualizações de uma
revisão antiga retornam 409, sem substituir a versão atual. Repetições idênticas são
idempotentes. A importação do mobile aceita `importacao: true` e mantém a data original;
ela também reconhece uma cópia antiga que já faz parte da conversa do servidor.

O mobile importa o histórico que estava no AsyncStorage quando o usuário abre a Lupe.
A cópia local só é removida após a confirmação do servidor. No desktop, entre na mesma
conta e abra **Lupe** no menu lateral. **Atualizar** busca o histórico atual; voltar à
aba do navegador também atualiza a lista e a conversa aberta quando não há envio pendente.

Os testes `tests/historico_lupe_backend.py` do projeto mobile usam SQLite temporário
e clientes Flask separados para cookie e Bearer, sem acessar os registros financeiros.
