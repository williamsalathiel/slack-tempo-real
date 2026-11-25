import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from escuta import filtrar  # noqa: E402

EU = "U1"


def ev(**k):
    return {"type": "message", "user": "U2", "text": "oi", "channel": "C", "ts": "1", **k}


def test_privado():
    assert filtrar(ev(channel_type="im"), EU)["onde"] == "privado"


def test_grupo():
    assert filtrar(ev(channel_type="mpim"), EU)["onde"] == "grupo privado"


def test_canal_sem_marcar():
    assert filtrar(ev(channel_type="channel"), EU) is None


def test_canal_marcado():
    assert filtrar(ev(channel_type="channel", text="<@U1> olha"), EU)["onde"].startswith("canal")


def test_mensagem_minha():
    assert filtrar(ev(channel_type="im", user="U1"), EU) is None


def test_bot():
    assert filtrar(ev(channel_type="im", bot_id="B"), EU) is None


def test_editada():
    assert filtrar(ev(channel_type="im", subtype="message_changed"), EU) is None
