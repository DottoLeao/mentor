import type { Passo, Trilha, Unidade } from "./tipos";
import { TYPESCRIPT_FUNDAMENTOS } from "./trilhas/typescript-fundamentos";

export const TRILHAS: Record<string, Trilha> = {
  [TYPESCRIPT_FUNDAMENTOS.id]: TYPESCRIPT_FUNDAMENTOS,
};

export function todosOsPassos(t: Trilha): { unidade: Unidade; passo: Passo }[] {
  return t.unidades.flatMap((unidade) => unidade.passos.map((passo) => ({ unidade, passo })));
}

export function acharPasso(t: Trilha, passoId: string): { unidade: Unidade; passo: Passo } | undefined {
  return todosOsPassos(t).find((p) => p.passo.id === passoId);
}
