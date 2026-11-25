"""Escuta o Slack em TEMPO REAL em nome de uma pessoa (Socket Mode + token de usuário).

Recebe na hora tudo que chega para você: mensagem no privado, em grupo privado e quando te marcam num canal.
Não precisa marcar nenhum bot: o app escuta "como você" (eventos de usuário), então qualquer mensagem que você
veria, ele vê.

Para cada mensagem que importa, ele:
  - imprime uma linha JSON (e grava em dados/eventos.jsonl), para o seu agente ler; e
  - se AGENTE_WEBHOOK_URL estiver no .env, faz um POST nessa URL (ex.: a automação do Grok com gatilho de webhook).

Uso:  python escuta.py          (deixa rodando; reconecta sozinho)
Tokens no arquivo .env ao lado (nunca suba esse arquivo):
  SLACK_APP_TOKEN=xapp-...      (token do app, escopo connections:write)
  SLACK_USER_TOKEN=xoxp-...     (token de usuário, depois de instalar o app)
  AGENTE_WEBHOOK_URL=...        (opcional)
  AGENTE_WEBHOOK_SEGREDO=whsec_... (opcional: assina no padrão Standard Webhooks)
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import websockets

AQUI = Path(__file__).resolve().parent
DADOS = AQUI / "dados"
NOMES: dict[str, str] = {}


def ler_env() -> dict:
    vals = {}
    arq = AQUI / ".env"
    if arq.exists():
        for linha in arq.read_text(encoding="utf-8").splitlines():
            if "=" in linha and not linha.lstrip().startswith("#"):
                k, v = linha.split("=", 1)
                vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals


def slack_api(metodo: str, token: str, **params) -> dict:
    req = urllib.request.Request(f"https://slack.com/api/{metodo}", data=urllib.parse.urlencode(params).encode(),
                                 headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def nome(uid: str, token: str) -> str:
    if uid not in NOMES:
        try:
            u = slack_api("users.info", token, user=uid).get("user") or {}
            p = u.get("profile") or {}
            NOMES[uid] = p.get("display_name") or u.get("real_name") or uid
        except Exception:
            NOMES[uid] = uid
    return NOMES[uid]


def filtrar(ev: dict, eu: str) -> dict | None:
    """Decide se a mensagem importa. Devolve o resumo, ou None para ignorar."""
    if ev.get("type") != "message" or ev.get("bot_id") or not ev.get("user"):
        return None
    if ev.get("subtype") not in (None, "file_share", "thread_broadcast"):
        return None  # edição, mensagem apagada, entrou no canal...
    if ev.get("user") == eu:
        return None  # mensagem sua
    texto = ev.get("text") or ""
    marcou = f"<@{eu}>" in texto or any(x in texto for x in ("<!here", "<!channel", "<!everyone"))
    tipo = ev.get("channel_type") or ""
    if tipo == "im":
        onde = "privado"
    elif tipo == "mpim":
        onde = "grupo privado"
    elif marcou:
        onde = "canal (te marcaram)"
    else:
        return None  # conversa de canal sem te marcar
    return {"onde": onde, "canal": ev.get("channel"), "ts": ev.get("ts"), "thread": ev.get("thread_ts") or "",
            "autor_id": ev.get("user"), "texto": texto[:3000], "tem_arquivo": bool(ev.get("files"))}


def avisar_webhook(msg: dict, env: dict) -> None:
    url = env.get("AGENTE_WEBHOOK_URL", "")
    if not url:
        return
    corpo = json.dumps({"tipo": "mensagem_slack", **msg}, ensure_ascii=False).encode()
    cab = {"Content-Type": "application/json"}
    segredo = env.get("AGENTE_WEBHOOK_SEGREDO", "")
    if segredo.startswith("whsec_"):  # Standard Webhooks: id.timestamp.corpo assinado com HMAC-SHA256
        wid, ts = f"msg_{uuid.uuid4().hex}", str(int(time.time()))
        chave = base64.b64decode(segredo.removeprefix("whsec_"))
        sig = base64.b64encode(hmac.new(chave, f"{wid}.{ts}.".encode() + corpo, hashlib.sha256).digest()).decode()
        cab |= {"webhook-id": wid, "webhook-timestamp": ts, "webhook-signature": f"v1,{sig}"}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=corpo, headers=cab), timeout=15) as r:
            print(f"  -> webhook HTTP {r.status}", flush=True)
    except Exception as e:
        print(f"  -> webhook falhou: {e}", flush=True)


async def escutar() -> None:
    espera = 5
    DADOS.mkdir(exist_ok=True)
    while True:
        env = ler_env()
        app, usuario = env.get("SLACK_APP_TOKEN", ""), env.get("SLACK_USER_TOKEN", "")
        if not app.startswith("xapp-") or not usuario.startswith("xoxp-"):
            print("Faltam SLACK_APP_TOKEN (xapp-...) e/ou SLACK_USER_TOKEN (xoxp-...) no .env", flush=True)
            return
        try:
            eu = slack_api("auth.test", usuario).get("user_id", "")
            r = slack_api("apps.connections.open", app)
            if not r.get("ok"):
                raise RuntimeError(r.get("error") or "apps.connections.open falhou")
            async with websockets.connect(r["url"], max_size=2 ** 22, ping_interval=30) as ws:
                print("Conectado ao Slack (Socket Mode). Esperando mensagens...", flush=True)
                espera = 5
                async for bruto in ws:
                    envelope = json.loads(bruto)
                    if envelope.get("envelope_id"):  # confirma o recebimento, senão o Slack reenvia
                        await ws.send(json.dumps({"envelope_id": envelope["envelope_id"]}))
                    if envelope.get("type") == "disconnect":
                        break  # o Slack pede para reconectar
                    if envelope.get("type") != "events_api":
                        continue
                    msg = filtrar((envelope.get("payload") or {}).get("event") or {}, eu)
                    if not msg:
                        continue
                    msg["autor"] = nome(msg["autor_id"], usuario)
                    linha = json.dumps(msg, ensure_ascii=False)
                    print(linha, flush=True)
                    with (DADOS / "eventos.jsonl").open("a", encoding="utf-8") as f:
                        f.write(linha + "\n")
                    await asyncio.to_thread(avisar_webhook, msg, env)
        except Exception as e:
            print(f"Caiu: {e}. Tento de novo em {espera} s", flush=True)
        await asyncio.sleep(espera)
        espera = min(espera * 2, 300)


if __name__ == "__main__":
    asyncio.run(escutar())
