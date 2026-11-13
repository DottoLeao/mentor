import { mkdir, mkdtemp, readdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { beforeEach, expect, test } from "vitest";
import { carregarMemoria, memoriaVazia, salvarMemoria } from "../../src/core/memoria";

let tmp: string;
beforeEach(async () => {
  tmp = await mkdtemp(join(tmpdir(), "mentor-"));
});

test("carregar sem arquivo devolve memória vazia", async () => {
  const { memoria, aviso } = await carregarMemoria(tmp);
  expect(memoria).toEqual(memoriaVazia("typescript-fundamentos"));
  expect(aviso).toBeUndefined();
});

test("salvar e carregar ida e volta", async () => {
  const m = { ...memoriaVazia("typescript-fundamentos"), concluidos: { "u1-x": { resultado: "sem_dica" as const, data: "2026-11-13" } } };
  await salvarMemoria(tmp, m);
  expect((await carregarMemoria(tmp)).memoria).toEqual(m);
});

test("JSON corrompido é preservado e gera aviso", async () => {
  await mkdir(join(tmp, ".mentor"), { recursive: true });
  await writeFile(join(tmp, ".mentor/progresso.json"), "{ quebrado");
  const { memoria, aviso } = await carregarMemoria(tmp);
  expect(aviso).toMatch(/corrompido/);
  expect(memoria.concluidos).toEqual({});
  const arquivos = await readdir(join(tmp, ".mentor"));
  expect(arquivos.some((f) => f.startsWith("progresso.json.corrompido-"))).toBe(true);
  expect(arquivos).not.toContain("progresso.json");
});

test("versão desconhecida também é preservada", async () => {
  await mkdir(join(tmp, ".mentor"), { recursive: true });
  await writeFile(join(tmp, ".mentor/progresso.json"), JSON.stringify({ versao: 99 }));
  const { aviso } = await carregarMemoria(tmp);
  expect(aviso).toMatch(/corrompido/);
});
