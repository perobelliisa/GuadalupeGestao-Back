# GuadalupeGestao-Back

## Documentação da API

Com o backend em execução, acesse http://localhost:5000/docs para abrir o
Swagger UI. A especificação OpenAPI está disponível em `/openapi.json`.
Reinicie o servidor após instalar esta alteração.

A documentação acompanha as rotas registradas no Flask e identifica parâmetros
de caminho, consultas, campos JSON, formulários, uploads e códigos de resposta.
Os campos são inferidos do código, inclusive dos validadores auxiliares; tipos,
obrigatoriedade e regras condicionais devem ser conferidos nos endpoints.
Rotas novas entram automaticamente no inventário. HEAD, OPTIONS e a rota
estática interna do Flask são omitidas.

Para testar rotas protegidas, execute `POST /login` no Swagger e use o cookie
recebido, ou informe um JWT no botão **Authorize**. As permissões existentes
continuam sendo verificadas. **Try it out** executa operações reais no banco.
O navegador precisa de internet para carregar os recursos do Swagger UI via CDN.

A interface usa a integração standalone descrita na
[documentação oficial do Swagger UI](https://swagger.io/docs/open-source-tools/swagger-ui/usage/installation/).


## Integração Arkhé

As credenciais ficam somente neste backend. Configure `ARKHE_API_URL`, `ARKHE_CLIENT_ID`
e `ARKHE_CLIENT_SECRET` no ambiente, ou copie `arkhe.local.example.json` para
`arkhe.local.json` (ignorado pelo Git) e preencha localmente. Reinicie o servidor.
Não use variáveis VITE para segredos. Cada conjunto de credenciais tem seu próprio histórico.

Ao iniciar, é criada a tabela Firebird `ARKHE_COBRANCA` se ainda não existir.
Rotas protegidas pelas permissões existentes de doações (tipos 0 e 1):

- `GET /integracoes/arkhe/conta`: validação da conta, apenas dados públicos.
- `GET /integracoes/arkhe/cobrancas`: histórico persistente da integração.
- `POST /integracoes/arkhe/cobrancas`: JSON com `id` UUID gerado pelo cliente,
  `doador`, `valor`, `id_projeto` opcional e `descricao` opcional.
- `POST /integracoes/arkhe/cobrancas/<uuid>/consultar`: consulta a Arkhé e,
  quando paga, registra doação e entrada na mesma transação, uma única vez.

Repetir o UUID de criação nunca repete o POST bancário. Se a resposta bancária se
perder, a solicitação fica para conferência manual; não há repetição automática.
A data contábil é a data da confirmação no Guadalupe (UTC-3), pois a consulta
documentada não informa a data do pagamento. O código recebido é interno da Arkhé.
Não há endpoint externo documentado para executar pagamentos de despesas.

Teste sem banco ou conta reais: `python -B -m unittest discover -s tests -p test_arkhe.py -v`.
