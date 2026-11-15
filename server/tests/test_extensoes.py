import re

from conftest import call
from mentor_server.extensoes import AVISO_VAZIO, carregar_catalogo, recomendar


def ids(lista):
    return [e.id for e in lista]


def test_erro_de_estilo_recomenda_eslint_primeiro():
    assert ids(recomendar("meu código tem erro de estilo"))[0] == "dbaeumer.vscode-eslint"


def test_git_commit_recomenda_gitlens():
    assert "eamodio.gitlens" in ids(recomendar("como vejo quem fez esse git commit?"))


def test_sem_diferenciar_maiusculas_e_acentos():
    assert ids(recomendar("FORMATACAO do arquivo"))[0] == "esbenp.prettier-vscode"


def test_ja_instalada_nao_volta():
    r = ids(recomendar("meu código tem erro de estilo", ja_instaladas=["DBAEUMER.vscode-eslint"]))
    assert "dbaeumer.vscode-eslint" not in r


def test_no_maximo_tres():
    assert len(recomendar("erro estilo lint formatar git commit ortografia typo eslint")) <= 3


def test_contexto_sem_casamento_devolve_vazio():  # Review Focus 1
    assert recomendar("quero uma extensão de música") == []


def test_catalogo_bem_formado():
    cat = carregar_catalogo()
    assert len(cat) >= 6
    for e in cat:
        assert re.fullmatch(r"[a-z0-9][a-z0-9-]*\.[a-z0-9][a-z0-9.-]*", e.id), e.id
        assert e.motivo.strip() and e.gatilhos and e.publicador.strip()
        assert e.url == f"https://marketplace.visualstudio.com/items?itemName={e.id}"
    assert len({e.id for e in cat}) == len(cat)


async def test_ferramenta_sem_casamento_da_aviso(client_sem_banco):  # Review Focus 1
    r = await call(client_sem_banco, "recomendar_extensao", {"contexto": "quero uma extensão de música"})
    assert not r.is_error
    assert r.data["extensoes"] == [] and r.data["aviso"] == AVISO_VAZIO


async def test_ferramenta_devolve_motivo(client_sem_banco):
    r = await call(client_sem_banco, "recomendar_extensao", {"contexto": "sublinhado vermelho no código"})
    e = r.data["extensoes"][0]
    assert e["id"] == "usernamehw.errorlens" and e["motivo"] and e["url"].startswith("https://marketplace")
    assert r.data["aviso"] == ""
