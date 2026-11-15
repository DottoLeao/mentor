import type { Passo, Trilha, Unidade } from "../tipos";

const RM_TS = "https://roadmap.sh/typescript";
const RM_CS = "https://roadmap.sh/computer-science";
const HR = "https://www.hackerrank.com/challenges";

function slug(s: string): string {
  return s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

interface Def {
  titulo: string;
  roadmapUrl: string;
  aulas: string[];
  exercicios: [titulo: string, hackerrank: string][];
  certificados?: string[];
}

function unidade(numero: number, d: Def): Unidade {
  const id = (s: string) => `u${numero}-${slug(s)}`;
  const passos: Passo[] = [
    ...d.aulas.map((a): Passo => ({ id: id(`aula-${a}`), tipo: "aula", titulo: a })),
    ...d.exercicios.map(([t, h]): Passo => ({ id: id(t), tipo: "exercicio", titulo: t, hackerrank: `${HR}/${h}` })),
    { id: id("prova"), tipo: "prova", titulo: `Prova da unidade ${numero}` },
    ...(d.certificados ?? []).map((c): Passo => ({ id: id(`certificado-${c}`), tipo: "certificado", titulo: `Certificado HackerRank: ${c}` })),
  ];
  return { id: `u${numero}`, numero, titulo: d.titulo, conceitos: d.aulas, roadmapUrl: d.roadmapUrl, passos };
}

const DEFS: Def[] = [
  {
    titulo: "Base da linguagem",
    roadmapUrl: RM_TS,
    aulas: ["Variáveis, let e const", "Tipos primitivos", "if/else", "for e while", "Funções com tipos"],
    exercicios: [
      ["Solve Me First", "solve-me-first"],
      ["Simple Array Sum", "simple-array-sum"],
      ["Compare the Triplets", "compare-the-triplets"],
      ["A Very Big Sum", "a-very-big-sum"],
      ["Time Conversion", "time-conversion"],
    ],
  },
  {
    titulo: "Arrays e strings",
    roadmapUrl: RM_TS,
    aulas: ["Índice e length", "for...of", "push, pop e slice", "split, join e includes", "Template strings"],
    exercicios: [
      ["Sales by Match", "sock-merchant"],
      ["Counting Valleys", "counting-valleys"],
      ["Diagonal Difference", "diagonal-difference"],
      ["Plus Minus", "plus-minus"],
      ["Staircase", "staircase"],
      ["Mini-Max Sum", "mini-max-sum"],
      ["Birthday Cake Candles", "birthday-cake-candles"],
    ],
  },
  {
    titulo: "Funções e objetos",
    roadmapUrl: RM_TS,
    aulas: ["Parâmetros, retorno e escopo", "Objetos e interface", "map, filter e reduce"],
    exercicios: [
      ["Grading Students", "grading"],
      ["Apple and Orange", "apple-and-orange"],
      ["Kangaroo", "kangaroo"],
      ["Breaking the Records", "breaking-best-and-worst-records"],
      ["Migratory Birds", "migratory-birds"],
    ],
  },
  {
    titulo: "Map, Set e contagem",
    roadmapUrl: RM_TS,
    aulas: ["Map", "Set", "Contagem de frequência"],
    exercicios: [
      ["Sales by Match com Map", "sock-merchant"],
      ["Two Strings", "two-strings"],
      ["Ice Cream Parlor", "ctci-ice-cream-parlor"],
    ],
    certificados: ["Problem Solving (Basic)"],
  },
  {
    titulo: "Ordenação e busca",
    roadmapUrl: RM_CS,
    aulas: ["sort com comparador", "Busca linear e binária"],
    exercicios: [
      ["Insertion Sort Part 1", "insertionsort1"],
      ["Find the Median", "find-the-median"],
      ["Closest Numbers", "closest-numbers"],
    ],
  },
  {
    titulo: "Recursão",
    roadmapUrl: RM_TS,
    aulas: ["Caso base e caso recursivo", "Pilha de chamadas"],
    exercicios: [
      ["Recursive Digit Sum", "recursive-digit-sum"],
      ["Fibonacci Modified", "fibonacci-modified"],
      ["The Power Sum", "the-power-sum"],
    ],
    certificados: ["JavaScript (Basic)", "SQL (Basic)"],
  },
  {
    titulo: "Pilhas, filas e listas",
    roadmapUrl: RM_TS,
    aulas: ["Pilha e fila", "Lista ligada"],
    exercicios: [
      ["Balanced Brackets", "balanced-brackets"],
      ["Queue using Two Stacks", "queue-using-two-stacks"],
      ["Reverse a linked list", "reverse-a-linked-list"],
    ],
  },
  {
    titulo: "Big O e padrões de entrevista",
    roadmapUrl: RM_CS,
    aulas: ["Big O", "Dois ponteiros e janela deslizante"],
    exercicios: [
      ["Pairs", "pairs"],
      ["Minimum Absolute Difference", "minimum-absolute-difference-in-an-array"],
      ["Max Min", "angry-children"],
    ],
    certificados: ["React (Basic)"],
  },
];

export const TYPESCRIPT_FUNDAMENTOS: Trilha = {
  id: "typescript-fundamentos",
  titulo: "Fundamentos em TypeScript",
  unidades: DEFS.map((d, i) => unidade(i + 1, d)),
};
