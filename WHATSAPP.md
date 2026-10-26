# WhatsApp com WAHA

O endpoint `POST /webhooks/waha` encaminha mensagens da sessão WAHA `default` ao
mesmo agente Lupe do aplicativo. O número autorizado por padrão é
`18981146999`, vinculado ao usuário Guadalupe `2`. A autorização também é
conferida pelas permissões já aplicadas às rotas financeiras.

## Variáveis no servidor do backend

Configure estas variáveis no ambiente em que o Flask roda:

```text
WAHA_API_URL=https://apps-guadalupe-waha.ucxocw.easypanel.host
WAHA_API_KEY=<chave da API WAHA>
WAHA_SESSION=default
WHATSAPP_ALLOWED_NUMBER=18981146999
WHATSAPP_USER_ID=2
WHATSAPP_WEBHOOK_SECRET=<segredo longo e aleatório>
WHATSAPP_TASK_SECRET=<outro segredo longo e aleatório>
```

Não publique a chave nem o segredo no repositório. `WHATSAPP_WEBHOOK_SECRET`
deve ser igual à chave HMAC configurada no webhook da sessão WAHA.

## Webhook da sessão WAHA

O backend precisa estar acessível pelo WAHA em HTTPS. Na configuração de
webhooks da sessão `default`, use o endereço público do backend terminado em
`/webhooks/waha`, evento `message` e a chave HMAC acima. Exemplo da configuração
da sessão (preserve as outras opções que já estiverem configuradas):

```json
{
  "name": "default",
  "config": {
    "webhooks": [
      {
        "url": "https://<endereco-publico-do-backend>/webhooks/waha",
        "events": ["message"],
        "hmac": {"key": "<mesmo WHATSAPP_WEBHOOK_SECRET>"},
        "retries": {"policy": "linear", "delaySeconds": 2, "attempts": 4}
      }
    ]
  }
}
```

Atualizar a configuração de uma sessão WAHA em execução pode reiniciá-la;
confira a configuração atual antes de substituir a lista de webhooks.

## Lembretes e resumo

Uma tarefa diária envia ao mesmo número um resumo das receitas e despesas do
dia anterior e lista contas vencidas ou com vencimento no dia. Configure um
agendador para fazer `POST https://<endereco-publico-do-backend>/tarefas/whatsapp/resumo-diario`
às 08:00 no fuso `America/Sao_Paulo`, enviando o cabeçalho
`X-Task-Secret: <WHATSAPP_TASK_SECRET>`. A tarefa evita repetir o resumo no
mesmo dia mesmo se o agendador chamar o endpoint mais de uma vez.

## Uso

Consultas são respondidas diretamente. Para qualquer escrita, a Lupe envia uma
proposta e um UUID. Envie `CONFIRMAR <UUID>` para executar ou `CANCELAR <UUID>`
para desistir. Respostas como “sim” não confirmam ações. As propostas expiram
conforme a mesma regra de 15 minutos usada no aplicativo.

O histórico de mensagens e a deduplicação de eventos usam o SQLite da Lupe,
normalmente `dados/lupe.sqlite3` ou o caminho configurado em `LUPE_DB_PATH`.

Para anexar um comprovante a uma despesa existente, envie PDF/JPG/PNG com a
legenda `COMPROVANTE <ID da despesa>`. O endpoint existente valida se o ID é
uma despesa e se o arquivo é permitido; o tamanho máximo é 12 MB.
