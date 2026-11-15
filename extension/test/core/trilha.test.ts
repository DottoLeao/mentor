import { expect, test } from "vitest";
import { TRILHAS, acharPasso, todosOsPassos } from "../../src/core/trilha";

const T = TRILHAS["typescript-fundamentos"];

test("trilha de TS tem 8 unidades na ordem da skill", () => {
  expect(T.unidades.map((u) => u.numero)).toEqual([1, 2, 3, 4, 5, 6, 7, 8]);
  expect(T.unidades[3].titulo).toBe("Map, Set e contagem");
});

test("ids de passo são únicos e cada unidade termina em prova ou certificado", () => {
  const passos = todosOsPassos(T);
  expect(new Set(passos.map((p) => p.passo.id)).size).toBe(passos.length);
  for (const u of T.unidades) expect(["prova", "certificado"]).toContain(u.passos.at(-1)!.tipo);
});

test("certificados nas unidades 4, 6 e 8", () => {
  const certs = todosOsPassos(T).filter((p) => p.passo.tipo === "certificado");
  expect(certs.map((c) => c.unidade.numero)).toEqual([4, 6, 6, 8]);
});

test("acharPasso devolve a unidade do passo", () => {
  expect(acharPasso(T, "u4-two-strings")?.unidade.numero).toBe(4);
  expect(acharPasso(T, "nao-existe")).toBeUndefined();
});

test("cada unidade tem link para o roadmap.sh", () => {
  for (const u of T.unidades) expect(u.roadmapUrl).toMatch(/^https:\/\/roadmap\.sh\//);
});
