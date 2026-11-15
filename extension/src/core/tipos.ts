export type TipoPasso = "aula" | "exercicio" | "prova" | "certificado";

export interface Passo {
  id: string;
  tipo: TipoPasso;
  titulo: string;
  hackerrank?: string;
}

export interface Unidade {
  id: string;
  numero: number;
  titulo: string;
  conceitos: string[];
  roadmapUrl: string;
  passos: Passo[];
}

export interface Trilha {
  id: string;
  titulo: string;
  unidades: Unidade[];
}
