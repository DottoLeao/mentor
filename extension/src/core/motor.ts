import type { Memoria, Resultado, Revisao } from "./memoria";
import { agendar, revisoesDoDia } from "./revisao";
import type { Passo, Trilha, Unidade } from "./tipos";
import { acharPasso, todosOsPassos } from "./trilha";

export type Proximo =
  | { tipo: "revisao"; revisoes: Revisao[] }
  | { tipo: "passo"; unidade: Unidade; passo: Passo }
  | { tipo: "fim" };

function copiar(m: Memoria): Memoria {
  return structuredClone(m);
}

export function proximoPasso(t: Trilha, m: Memoria, hoje: string): Proximo {
  const vencidas = revisoesDoDia(m, hoje);
  if (vencidas.length) return { tipo: "revisao", revisoes: vencidas };
  const proximo = todosOsPassos(t).find((p) => !m.concluidos[p.passo.id]);
  return proximo ? { tipo: "passo", ...proximo } : { tipo: "fim" };
}

/** `alvo` é um id de passo da trilha ou o nome livre de um item de revisão. */
export function registrarResultado(t: Trilha, m: Memoria, alvo: string, resultado: Resultado, hoje: string): Memoria {
  const nova = copiar(m);
  if (acharPasso(t, alvo) && resultado !== "refazer") {
    nova.concluidos[alvo] = { resultado, data: hoje };
  }
  const existente = nova.revisoes.find((r) => r.item === alvo);
  const { proxima, intervalo } = agendar(resultado, existente?.intervalo ?? 0, hoje, !!existente);
  const linha: Revisao = { item: alvo, ultima: hoje, resultado, proxima, intervalo };
  if (existente) Object.assign(existente, linha);
  else nova.revisoes.push(linha);
  return nova;
}

export function registrarNivelamento(t: Trilha, m: Memoria, unidadesDominadas: number[], hoje: string): Memoria {
  const nova = copiar(m);
  for (const u of t.unidades) {
    if (!unidadesDominadas.includes(u.numero)) continue;
    for (const p of u.passos) {
      if (p.tipo !== "certificado" && !nova.concluidos[p.id]) {
        nova.concluidos[p.id] = { resultado: "nivelamento", data: hoje };
      }
    }
  }
  nova.nivelamentoFeito = true;
  return nova;
}

export function registrarErro(m: Memoria, descricao: string, hoje: string): Memoria {
  const nova = copiar(m);
  const chave = descricao.trim().toLowerCase();
  const existente = nova.erros.find((e) => e.descricao.trim().toLowerCase() === chave);
  if (existente) {
    existente.vezes += 1;
    existente.ultima = hoje;
  } else {
    nova.erros.push({ descricao: descricao.trim(), vezes: 1, ultima: hoje });
  }
  return nova;
}
