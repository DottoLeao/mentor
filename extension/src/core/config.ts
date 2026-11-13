import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { PASTA } from "./memoria";

export interface ConfigPessoal {
  nome?: string;
  minutosPorDia?: number;
  metas: string[];
  prazos: { descricao: string; data: string }[];
}

const PADRAO: ConfigPessoal = { metas: [], prazos: [] };

/** Lê `.mentor/config.json`. Ausente ou inválido vira o padrão: a config é opcional. */
export async function carregarConfig(dir: string): Promise<ConfigPessoal> {
  try {
    const dados = JSON.parse(await readFile(join(dir, PASTA, "config.json"), "utf8"));
    return {
      ...(typeof dados.nome === "string" ? { nome: dados.nome } : {}),
      ...(typeof dados.minutosPorDia === "number" ? { minutosPorDia: dados.minutosPorDia } : {}),
      metas: Array.isArray(dados.metas) ? dados.metas.filter((x: unknown) => typeof x === "string") : [],
      prazos: Array.isArray(dados.prazos) ? dados.prazos : [],
    };
  } catch {
    return { ...PADRAO, metas: [], prazos: [] };
  }
}
