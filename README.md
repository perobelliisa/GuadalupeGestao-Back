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
