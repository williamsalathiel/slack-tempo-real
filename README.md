# Slack em tempo real para o seu agente

Faz o seu agente de IA receber **na hora** as mensagens do Slack que chegam para você (privado, grupo privado e quando te marcam num canal), **sem precisar marcar bot nenhum** e sem rotina varrendo o Slack.

## Como funciona

- Um **app do Slack** que escuta **como você** (eventos de usuário): tudo que chega para você chega para o app.
- **Socket Mode**: um programa no seu computador (`escuta.py`) abre uma conexão com o Slack e recebe os eventos em 1 ou 2 segundos. Não precisa de servidor, URL pública nem túnel.
- O programa filtra o que importa, grava em `dados/eventos.jsonl` e, se você quiser, manda cada mensagem para o seu agente por **webhook** (ex.: uma automação do Grok).

## Como usar

Cole o [`SKILL.md`](SKILL.md) no Claude Code, Codex ou outra IA e peça: "me ajuda a montar isso". Ela te guia passo a passo:

1. criar o app no Slack com o [`manifest.json`](manifest.json) (já vem com os escopos e eventos certos);
2. pegar os dois tokens (`xapp-...` e `xoxp-...`) e pôr no `.env`;
3. rodar `python escuta.py`;
4. (opcional) ligar no Grok pelo webhook.

## Grok

O Grok roda na nuvem e não segura a conexão com o Slack sozinho. Então o `escuta.py` fica no seu computador e repassa cada mensagem para uma automação do Grok com gatilho de webhook (assinada no padrão Standard Webhooks, se você tiver o `whsec_`). O passo a passo está na etapa 3 do `SKILL.md`.

## Segurança

- Os tokens ficam só no `.env` (já ignorado pelo git).
- O app só **lê**. Responder sozinho é outra etapa e fica a seu critério.

Licença MIT.
