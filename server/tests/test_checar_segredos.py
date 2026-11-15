import importlib.util
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "checar_segredos.py"
_spec = importlib.util.spec_from_file_location("checar_segredos", SCRIPT)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def test_todos_presentes():
    assert mod.checar_segredos(["A", "B"], {"A": "1", "B": "2"}) == []


def test_vazio_e_faltando_contam_como_ausentes():
    assert mod.checar_segredos(["A", "B", "C"], {"A": "", "B": "  ", "D": "x"}) == ["A", "B", "C"]


def _rodar(env_extra, tmp_path, *nomes):
    saida = tmp_path / "github_output"
    env = {"PATH": "", "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", ""), "GITHUB_OUTPUT": str(saida),
           **env_extra}
    r = subprocess.run([sys.executable, str(SCRIPT), *nomes], env=env, capture_output=True, text=True)
    return r, saida.read_text() if saida.exists() else ""


def test_script_sem_segredos_pula_com_aviso_e_sai_0(tmp_path):  # Review Focus 2
    r, out = _rodar({"DATABASE_URL": "postgres://segredo"}, tmp_path, "DATABASE_URL", "CF_ACCOUNT_ID", "CF_API_TOKEN")
    assert r.returncode == 0
    assert "Segredo CF_ACCOUNT_ID ausente, pulando." in r.stdout
    assert "Segredo CF_API_TOKEN ausente, pulando." in r.stdout
    assert "postgres://segredo" not in r.stdout + r.stderr  # nada vaza
    assert "pular=true" in out


def test_script_com_tudo_nao_pula(tmp_path):
    r, out = _rodar({"A": "1", "B": "2"}, tmp_path, "A", "B")
    assert r.returncode == 0 and "pular=false" in out and "ausente" not in r.stdout
