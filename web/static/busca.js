// Sugestões de nome enquanto se digita, consumindo `GET /api/v1/monstros?nome=`.
//
// É um dos dois consumidores internos da API — o outro é o link JSON de cada
// ficha. Sem eles a API seria decorativa, que é pior que não ter API nenhuma.
//
// Sem framework e sem etapa de compilação: o campo já funciona como formulário
// comum, e isto só acrescenta as sugestões. Se o fetch falhar, o formulário
// continua enviando normalmente.

const campo = document.querySelector('.busca input[name="nome"]');
const sugestoes = document.getElementById("sugestoes-de-monstro");

if (campo && sugestoes) {
  let ultimaBusca = null;

  campo.addEventListener("input", async () => {
    const trecho = campo.value.trim();
    if (trecho.length < 2) {
      sugestoes.innerHTML = "";
      return;
    }

    // Guarda qual busca disparou esta chamada: respostas fora de ordem
    // sobrescreveriam a lista com o resultado de um texto já apagado.
    const buscaAtual = trecho;
    ultimaBusca = buscaAtual;

    try {
      const resposta = await fetch(
        `/api/v1/monstros?nome=${encodeURIComponent(trecho)}&limite=10`
      );
      if (!resposta.ok || ultimaBusca !== buscaAtual) return;

      const corpo = await resposta.json();
      sugestoes.innerHTML = "";
      for (const monstro of corpo.itens) {
        const opcao = document.createElement("option");
        opcao.value = monstro.nome;
        sugestoes.appendChild(opcao);
      }
    } catch {
      // Rede fora não pode quebrar a página: o formulário ainda envia.
      sugestoes.innerHTML = "";
    }
  });
}
