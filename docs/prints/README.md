# docs/prints: prints do app (gerados em 2026-11-08)

Capturas geradas automaticamente com Streamlit headless + Playwright (nenhuma
chave aparece nos prints: o `conversa.png` mostra apenas a input vazia e a
resposta do agente):

Esta pasta é reservada para os prints de divulgação do projeto:

| Arquivo | O que mostra |
|---------|--------------|
| `painel.png` | Aba **Painel**: cards de KPIs (receita total R$ 733.288,00, 150 pedidos, ticket médio R$ 4.888,59, 29 clientes), filtros e gráficos Plotly (receita por categoria, top-5 cidades, receita mensal, distribuição de status). |
| `conversa.png` | Aba **Conversa**: pergunta em português (“qual a receita total?”) respondida pelo agente com o número vindo de `receita_total` (tool-calling ao vivo via OpenRouter). O expander de chave está recolhido (sem chave visível). |
| `arquitetura.png` | Diagrama de arquitetura renderizado do [architecture.mermaid](../architecture.mermaid). |

## Como regenerar

```bash
pip install -r requirements.txt
streamlit run src/data_pilot/app.py
```

- `painel.png`: suba o app sem chave e capture a aba **Painel**.
- `conversa.png`: configure `OPENROUTER_API_KEY` no `.env` (ou cole a chave no
  expander “🔑 Chave do OpenRouter” na própria tela: ela só vive na memória da
  sessão), faça uma pergunta e capture a aba **Conversa**.
- `arquitetura.png`: exporte o Mermaid (abra em [mermaid.live](https://mermaid.live/)
  ou use a ferramenta que renderiza este repo).

Os READMEs referenciam `docs/prints/painel.png`, `conversa.png` e `arquitetura.png`.
