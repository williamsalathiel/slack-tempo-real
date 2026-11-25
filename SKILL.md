---
name: slack-tempo-real
description: Faz o agente da pessoa receber em tempo real as mensagens do Slack que chegam para ela (privado, grupo e quando a marcam), sem precisar marcar nenhum bot e sem rotina varrendo o Slack. Cria o app do Slack (Socket Mode + eventos de usuário), roda o escutador e, se quiser, repassa cada mensagem para o Grok (ou outro agente) por webhook. Use quando pedirem "meu agente receber as mensagens do Slack na hora".
---

# Slack em tempo real para o seu agente

Este arquivo serve para colar num chat (Claude Code, Codex ou outra IA) ou para usar como skill. Siga as etapas na ordem e confirme cada uma antes de passar para a próxima.

## Como funciona (explique isto à pessoa em 3 linhas)

- Você cria um **app do Slack** que escuta **como você** (eventos de usuário). Por isso não precisa marcar bot nenhum: tudo que chega para você chega para o app.
- O app usa **Socket Mode**: em vez de o Slack chamar uma URL pública, um programa no seu computador abre uma conexão com o Slack e recebe os eventos na hora. Não precisa de servidor nem de túnel.
- O programa (`escuta.py`) filtra o que importa (privado, grupo privado e canal em que te marcaram), grava e, se você quiser, manda para o seu agente (ex.: Grok) por webhook.

## Regras

1. Tokens (`xapp-...`, `xoxp-...`, `whsec_...`) ficam só no arquivo `.env`. Nunca no chat, no git ou em issue. Se a pessoa colar um token no chat, avise que deve trocar depois.
2. Um comando por vez; confira a saída antes de seguir.
3. Responder mensagens sozinho é outra etapa: este guia só faz o agente **receber**. Não ligue resposta automática sem a pessoa pedir.

## Etapa 1: criar o app no Slack

1. Abra https://api.slack.com/apps → **Create New App** → **From a manifest**.
2. Escolha o workspace e cole o conteúdo de `manifest.json` (pode trocar o nome "Meu agente").
3. **Create** → **Install to Workspace** → **Allow**. Se o workspace exigir aprovação de admin, peça ao admin.
4. Em **OAuth & Permissions**, copie o **User OAuth Token** (começa com `xoxp-`).
5. Em **Basic Information → App-Level Tokens → Generate Token and Scopes**: nome "socket", escopo `connections:write` → copie o token (começa com `xapp-`).

## Etapa 2: rodar o escutador

Precisa de Python 3.10+.

```bash
git clone https://github.com/williamsalathiel/slack-tempo-real.git
cd slack-tempo-real
python3 -m venv venv && source venv/bin/activate      # Windows: py -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
cp .env.exemplo .env                                   # Windows: copy .env.exemplo .env
```

Peça à pessoa para preencher o `.env` ela mesma (não peça os tokens no chat). Depois:

```bash
python escuta.py
```

Deve aparecer `Conectado ao Slack (Socket Mode)`. Peça para alguém mandar uma mensagem no privado da pessoa: em 1 ou 2 segundos aparece uma linha JSON com autor, onde e texto (e ela fica em `dados/eventos.jsonl`).

Para deixar rodando sempre: no Mac, um LaunchAgent; no Windows, o Agendador de Tarefas ("ao fazer logon"). Só crie isso se a pessoa quiser.

## Etapa 3 (opcional): mandar para o Grok

O Grok roda na nuvem e não consegue manter a conexão com o Slack sozinho. Então o `escuta.py` fica no computador e **repassa** cada mensagem para uma automação do Grok:

1. No Grok, crie uma automação com gatilho **webhook**; copie a URL e, se houver, o segredo de assinatura (`whsec_...`).
2. No `.env`, preencha `AGENTE_WEBHOOK_URL` e `AGENTE_WEBHOOK_SEGREDO`.
3. Nas instruções da automação, diga o que fazer, por exemplo: "Você recebe mensagens do Slack que chegaram para mim (campo `texto`, `autor`, `onde`). Resuma e me avise; não responda ninguém sem eu pedir."
4. Teste mandando uma mensagem no privado: o `escuta.py` mostra `-> webhook HTTP 200` e a automação do Grok roda.

Sem computador ligado: dá para trocar o Socket Mode por **Request URL** (o Slack chama uma URL), mas o Slack exige responder um "challenge" na primeira chamada, coisa que o webhook do Grok não faz. Aí precisa de um intermediário (por exemplo um Cloudflare Worker) que responda o challenge e repasse para o Grok. Só siga por aí se a pessoa pedir.

## Problemas comuns

- `invalid_auth` / `not_authed`: token errado ou com espaço; confira o `.env`.
- `missing_scope`: o app foi instalado antes de mudar os escopos; reinstale em **Install App**.
- Conecta mas não chega nada: confira em **Event Subscriptions** se os 4 eventos estão em "Subscribe to events on behalf of users" e se o **Socket Mode** está ligado.
- Só um programa por app: se dois `escuta.py` rodarem com o mesmo app, o Slack divide os eventos entre eles.
