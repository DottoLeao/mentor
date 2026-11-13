import { memoriaVazia, type Memoria, type Revisao } from "./memoria";
import { registrarNivelamento } from "./motor";
import type { Trilha } from "./tipos";

const DATA = /\d{4}-\d{2}-\d{2}/;

function secoes(md: string): Map<string, string[]> {
  const mapa = new Map<string, string[]>();
  let atual: string | undefined;
  for (const linha of md.split(/\r?\n/)) {
    const m = /^##\s+(.+?)\s*$/.exec(linha);
    if (m && !linha.startsWith("###")) {
      atual = m[1].toLowerCase();
      mapa.set(atual, []);
    } else if (atual) {
      mapa.get(atual)!.push(linha);
    }
  }
  return mapa;
}

function itens(linhas: string[] = []): string[] {
  return linhas.filter((l) => /^\s*-\s+/.test(l)).map((l) => l.replace(/^\s*-\s+/, "").trim());
}

function dias(de: string, ate: string): number {
  return Math.round((Date.parse(`${ate}T00:00:00Z`) - Date.parse(`${de}T00:00:00Z`)) / 86_400_000);
}

function revisoes(linhas: string[] = []): Revisao[] {
  const out: Revisao[] = [];
  for (const l of linhas) {
    if (!l.trim().startsWith("|")) continue;
    const cel = l.split("|").slice(1, -1).map((c) => c.trim());
    if (cel.length < 4) continue;
    const ultima = DATA.exec(cel[1])?.[0];
    const proxima = DATA.exec(cel[3])?.[0];
    if (!ultima || !proxima) continue; // cabeçalho e separador
    out.push({ item: cel[0], ultima, resultado: cel[2], proxima, intervalo: Math.max(1, dias(ultima, proxima)) });
  }
  return out;
}

/** Converte o diário em Markdown da skill /mentor para a memória do Mentor. */
export function importarDiario(md: string, t: Trilha, hoje: string): Memoria {
  const s = secoes(md);
  let m: Memoria = memoriaVazia(t.id);
  m.domina = itens(s.get("domina"));
  m.emAndamento = itens(s.get("em andamento"));
  m.revisoes = revisoes(s.get("revisões") ?? s.get("revisoes"));
  m.sessoes = (s.get("sessões") ?? s.get("sessoes") ?? [])
    .map((l) => /^###\s+(\d{4}-\d{2}-\d{2})\s*(?:\((.*)\))?/.exec(l))
    .filter((x): x is RegExpExecArray => !!x)
    .map((x) => ({ data: x[1], resumo: x[2] ?? "" }));
  const semana = Number(/Semana atual:\s*(\d+)/.exec(md)?.[1] ?? "1");
  const anteriores = Array.from({ length: Math.max(0, semana - 1) }, (_, i) => i + 1);
  m = registrarNivelamento(t, m, anteriores, hoje);
  m.nivelamentoFeito = true;
  return m;
}
