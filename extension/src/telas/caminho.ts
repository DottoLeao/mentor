import type { Memoria } from "../core/memoria";
import { proximoPasso } from "../core/motor";
import { revisoesDoDia } from "../core/revisao";
import type { Passo, Trilha } from "../core/tipos";
import { esc, pagina } from "./estilo";

/** Deslocamentos do zigue-zague; as classes d0..d7 ficam no CSS (a CSP bloqueia style= inline). */
export const DESLOC = [0, 50, 90, 50, 0, -50, -90, -50];
const ICONE: Record<Passo["tipo"], string> = { aula: "A", exercicio: "{ }", prova: "P", certificado: "★" };

/** Caminho linear: unidades em faixas, passos em zigue-zague, passos futuros visíveis. */
export function renderCaminho(t: Trilha, m: Memoria, hoje: string, nonce: string): string {
  // O passo atual da trilha ignora as revisões: elas aparecem no aviso acima do caminho.
  const prox = proximoPasso(t, { ...m, revisoes: [] }, hoje);
  const atualId = prox.tipo === "passo" ? prox.passo.id : undefined;
  const atualUnidade = prox.tipo === "passo" ? prox.unidade.numero : Infinity;
  const vencidas = revisoesDoDia(m, hoje).length;

  const unidades = t.unidades
    .map((u) => {
      const feitos = u.passos.filter((p) => m.concluidos[p.id]).length;
      const classe = feitos === u.passos.length ? "concluida" : u.numero === atualUnidade ? "agora" : "depois";
      const rotulo = classe === "concluida" ? "concluída" : classe === "agora" ? "agora" : "a seguir";
      const passos = u.passos
        .map((p, i) => {
          const estado = m.concluidos[p.id] ? "concluído" : p.id === atualId ? "você está aqui" : "bloqueado";
          const cls = m.concluidos[p.id] ? "concluido" : p.id === atualId ? "atual" : "bloqueado";
          const icone = cls === "concluido" ? "✓" : cls === "bloqueado" ? "🔒" : ICONE[p.tipo];
          const extra = cls === "atual" ? `<button id="comecar">Começar no Claude Code</button>` : "";
          return `<div class="passo ${cls} d${i % DESLOC.length}">
  <div class="bola" aria-hidden="true">${icone}</div>
  <strong>${esc(p.titulo)}</strong><span class="estado">${estado}</span>${extra}</div>`;
        })
        .join("\n");
      return `<section>
<div class="faixa ${classe}"><div><div class="estado">Unidade ${u.numero} · ${rotulo}</div><h2>${esc(u.titulo)}</h2></div>
<div class="estado">${feitos} de ${u.passos.length}<br><a href="${esc(u.roadmapUrl)}">ver no roadmap.sh</a></div></div>
<div class="passos">${passos}</div></section>`;
    })
    .join("\n");

  const aviso = vencidas
    ? `<div class="aviso">${vencidas} ${vencidas === 1 ? "revisão" : "revisões"} para hoje. O Mentor começa por elas antes do próximo passo.</div>`
    : "";
  const fim = prox.tipo === "fim" ? `<div class="aviso">Você terminou a trilha ${esc(t.titulo)}.</div>` : "";
  const script = `const vs=acquireVsCodeApi();document.getElementById("comecar")?.addEventListener("click",()=>vs.postMessage({tipo:"comecar"}));`;
  return pagina("Mentor · Caminho", nonce, `<h1>${esc(t.titulo)}</h1>${aviso}${fim}${unidades}`, script);
}
