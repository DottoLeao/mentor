"""Confere se os segredos de um workflow existem, sem nunca imprimir o valor.

Uso: python scripts/checar_segredos.py NOME [NOME ...]
Imprime "Segredo <X> ausente, pulando." para cada ausente e escreve pular=true|false
em $GITHUB_OUTPUT. Sempre sai com código 0: segredo ausente (fork, PR de terceiro)
não é falha de CI.
"""

import os
import sys
from collections.abc import Mapping


def checar_segredos(nomes: list[str], env: Mapping[str, str]) -> list[str]:
    """Devolve os nomes ausentes; valor vazio ou só espaços conta como ausente."""
    return [n for n in nomes if not (env.get(n) or "").strip()]


def main(argv: list[str]) -> int:
    ausentes = checar_segredos(argv, os.environ)
    for nome in ausentes:
        print(f"Segredo {nome} ausente, pulando.")
    saida = os.environ.get("GITHUB_OUTPUT")
    if saida:
        with open(saida, "a", encoding="utf-8") as f:
            f.write(f"pular={'true' if ausentes else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
