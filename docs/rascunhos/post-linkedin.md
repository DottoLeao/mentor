# Rascunho: post do LinkedIn (MENTOR-38)

Status: rascunho. Não publicado. Publicar só depois do merge dos PRs e, de preferência, com o vídeo de 20 s.

---

Eu construí um mentor de programação que se recusa a escrever o código por você.

Muita gente começa a programar hoje pedindo tudo para a IA. O código roda, mas a pessoa pula etapas e não sabe explicar o que fez. Na primeira entrevista técnica, o buraco aparece.

O Mentor fica dentro do VS Code, conversa em português pelo Claude Code e faz o que um bom mentor faria:

- dá dicas em camadas e só mostra a resposta se você pedir;
- lembra o que você já domina e os erros que se repetem, num arquivo que fica na sua máquina;
- explica cada conceito com um trecho citado da documentação oficial (MDN, TypeScript, Node.js e VS Code), com link.

Por baixo: um servidor MCP em Python com busca híbrida (vetor + full-text) e uma extensão do VS Code com MCP local.

Os números, medidos e sem arredondar para cima: recall@5 de 0,95 e MRR de 0,75 em 20 perguntas, num índice com mais de 21 mil trechos. São 158 testes automatizados. A avaliação das conversas ainda não rodou, e está escrito no README o que falta.

O código é aberto: https://github.com/DottoLeao/mentor

#Python #RAG #VSCode
