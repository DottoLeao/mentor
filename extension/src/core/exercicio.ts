import { mkdir, writeFile } from "node:fs/promises";
import { join, relative, resolve, isAbsolute } from "node:path";

export interface EspecExercicio {
  nome: string;
  titulo: string;
  enunciado: string;
  exemplo: string;
  perguntaGuia: string;
  funcao: string;
  parametros: string;
  retorno: string;
  casos: { entrada: string; esperado: string; borda?: boolean }[];
  hackerrank?: string;
}

const NOME = /^[a-z0-9][a-z0-9-]*$/;
const IDENT = /^[A-Za-z_$][\w$]*$/;

function validar(e: EspecExercicio): void {
  if (!NOME.test(e.nome)) throw new Error("O nome do exercício só pode ter letras minúsculas, números e hífen.");
  if (!IDENT.test(e.funcao)) throw new Error("O nome da função não é um identificador válido.");
  if (!e.casos.some((c) => c.borda)) throw new Error("Inclua pelo menos um caso de borda (vazio, repetido ou negativo).");
}

/** Gera o arquivo no formato da skill: enunciado, assinatura tipada e testes no fim. */
export function gerarExercicio(e: EspecExercicio): string {
  validar(e);
  const casos = e.casos
    .map((c) => `  [${c.entrada}, ${c.esperado}],${c.borda ? " // caso de borda" : ""}`)
    .join("\n");
  return `/**
 * ${e.titulo}${e.hackerrank ? ` (HackerRank: ${e.hackerrank})` : ""}
 *
 * ${e.enunciado}
 * Exemplo: ${e.exemplo}
 *
 * Dica para começar: pense primeiro sem código. ${e.perguntaGuia}
 */

export function ${e.funcao}(${e.parametros}): ${e.retorno} {
  // seu código aqui
}

// ---------- testes (rode: node ${e.nome}.ts) ----------
const casos: Array<[Parameters<typeof ${e.funcao}>[0], ReturnType<typeof ${e.funcao}>]> = [
${casos}
];
for (const [entrada, esperado] of casos) {
  const obtido = ${e.funcao}(entrada);
  const ok = JSON.stringify(obtido) === JSON.stringify(esperado);
  console.log(ok ? "✅" : "❌", JSON.stringify(entrada), "→", obtido, ok ? "" : \`(esperado \${esperado})\`);
}
`;
}

/** Cria `<dir>/<pasta>/<nome>.ts`. Nunca sobrescreve e nunca sai da pasta do workspace. */
export async function criarArquivoExercicio(dir: string, pasta: string, e: EspecExercicio): Promise<string> {
  const conteudo = gerarExercicio(e);
  const alvoPasta = resolve(dir, pasta);
  const rel = relative(resolve(dir), alvoPasta);
  if (rel.startsWith("..") || isAbsolute(rel)) {
    throw new Error("A pasta do exercício precisa ficar dentro da pasta de estudos aberta no VS Code.");
  }
  await mkdir(alvoPasta, { recursive: true });
  const caminho = join(alvoPasta, `${e.nome}.ts`);
  try {
    await writeFile(caminho, conteudo, { encoding: "utf8", flag: "wx" });
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === "EEXIST") throw new Error(`O arquivo ${caminho} já existe. Escolha outro nome.`);
    throw err;
  }
  return caminho;
}
