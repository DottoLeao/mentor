import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { join } from "node:path";

export type Resultado = "sem_dica" | "com_dica" | "refazer";

export interface Revisao {
  item: string;
  ultima: string;
  resultado: string;
  proxima: string;
  intervalo: number;
}

export interface Memoria {
  versao: 1;
  trilha: string;
  concluidos: Record<string, { resultado: Resultado | "nivelamento"; data: string }>;
  domina: string[];
  emAndamento: string[];
  erros: { descricao: string; vezes: number; ultima: string }[];
  revisoes: Revisao[];
  sessoes: { data: string; resumo: string }[];
  nivelamentoFeito: boolean;
}

export const PASTA = ".mentor";
const ARQUIVO = "progresso.json";

export function memoriaVazia(trilha: string): Memoria {
  return {
    versao: 1,
    trilha,
    concluidos: {},
    domina: [],
    emAndamento: [],
    erros: [],
    revisoes: [],
    sessoes: [],
    nivelamentoFeito: false,
  };
}

function valida(x: unknown): x is Memoria {
  const m = x as Memoria;
  return (
    !!m &&
    m.versao === 1 &&
    typeof m.trilha === "string" &&
    typeof m.concluidos === "object" &&
    Array.isArray(m.domina) &&
    Array.isArray(m.emAndamento) &&
    Array.isArray(m.erros) &&
    Array.isArray(m.revisoes) &&
    Array.isArray(m.sessoes)
  );
}

export async function carregarMemoria(dir: string, trilhaPadrao = "typescript-fundamentos"): Promise<{ memoria: Memoria; aviso?: string }> {
  const caminho = join(dir, PASTA, ARQUIVO);
  let texto: string;
  try {
    texto = await readFile(caminho, "utf8");
  } catch {
    return { memoria: memoriaVazia(trilhaPadrao) };
  }
  try {
    const dados = JSON.parse(texto);
    if (valida(dados)) return { memoria: dados };
  } catch {
    // cai no tratamento de arquivo corrompido
  }
  const copia = `${caminho}.corrompido-${new Date().toISOString().replace(/[:.]/g, "-")}`;
  await rename(caminho, copia);
  return {
    memoria: memoriaVazia(trilhaPadrao),
    aviso: `O arquivo de progresso estava corrompido. Guardei uma cópia em ${copia} e comecei um progresso novo.`,
  };
}

export async function salvarMemoria(dir: string, m: Memoria): Promise<void> {
  const pasta = join(dir, PASTA);
  await mkdir(pasta, { recursive: true });
  const tmp = join(pasta, `${ARQUIVO}.tmp`);
  await writeFile(tmp, JSON.stringify(m, null, 2), "utf8");
  await rename(tmp, join(pasta, ARQUIVO));
}
