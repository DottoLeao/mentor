import { mkdtemp, readFile, writeFile, mkdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { beforeEach, expect, test } from "vitest";
import { carregarConfig } from "../../src/core/config";
import { criarArquivoExercicio, gerarExercicio, type EspecExercicio } from "../../src/core/exercicio";

const ESPEC: EspecExercicio = {
  nome: "contar-pares",
  titulo: "Contar pares",
  enunciado: "Conte quantos pares de meias da mesma cor existem.",
  exemplo: "[10, 20, 20, 10] → 2",
  perguntaGuia: "Como você contaria isso numa folha de papel?",
  funcao: "contarPares",
  parametros: "ar: number[]",
  retorno: "number",
  casos: [
    { entrada: "[10, 20, 20, 10]", esperado: "2" },
    { entrada: "[]", esperado: "0", borda: true },
  ],
  hackerrank: "https://www.hackerrank.com/challenges/sock-merchant",
};

let tmp: string;
beforeEach(async () => {
  tmp = await mkdtemp(join(tmpdir(), "mentor-"));
});

test("gera no formato da skill", () => {
  const src = gerarExercicio(ESPEC);
  expect(src).toContain("export function contarPares(ar: number[]): number {");
  expect(src).toContain("// seu código aqui");
  expect(src).toContain("rode: node contar-pares.ts");
  expect(src).toMatch(/caso de borda/);
  expect(src).toContain("https://www.hackerrank.com/challenges/sock-merchant");
});

test("sem caso de borda é recusado", () => {
  expect(() => gerarExercicio({ ...ESPEC, casos: [{ entrada: "[1]", esperado: "0" }] })).toThrow(/caso de borda/);
});

test("nome inválido é recusado", () => {
  expect(() => gerarExercicio({ ...ESPEC, nome: "../x" })).toThrow(/nome/);
});

test("cria o arquivo na pasta e não sobrescreve", async () => {
  const caminho = await criarArquivoExercicio(tmp, "semana-4", ESPEC);
  expect(caminho).toBe(join(tmp, "semana-4", "contar-pares.ts"));
  expect(await readFile(caminho, "utf8")).toContain("contarPares");
  await expect(criarArquivoExercicio(tmp, "semana-4", ESPEC)).rejects.toThrow(/já existe/);
});

test("pasta fora do workspace é recusada", async () => {
  await expect(criarArquivoExercicio(tmp, "../fora", ESPEC)).rejects.toThrow(/dentro da pasta/);
});

test("config ausente ou inválida vira padrão", async () => {
  expect(await carregarConfig(tmp)).toEqual({ metas: [], prazos: [] });
  await mkdir(join(tmp, ".mentor"), { recursive: true });
  await writeFile(join(tmp, ".mentor/config.json"), "{ ruim");
  expect(await carregarConfig(tmp)).toEqual({ metas: [], prazos: [] });
});

test("config válida é lida", async () => {
  await mkdir(join(tmp, ".mentor"), { recursive: true });
  await writeFile(join(tmp, ".mentor/config.json"), JSON.stringify({ nome: "Ana", metas: ["Certificado X"], prazos: [] }));
  expect(await carregarConfig(tmp)).toEqual({ nome: "Ana", metas: ["Certificado X"], prazos: [] });
});
