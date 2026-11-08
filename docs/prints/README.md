# docs/prints — prints do app (a completar após rodar o app)

Esta pasta é reservada para os prints de divulgação do projeto:

| Arquivo | O que mostra |
|---------|--------------|
| `painel.png` | Aba **Painel**: cards de KPIs (receita total, pedidos concluídos, ticket médio, clientes únicos), filtros de categoria/período/status e gráficos Plotly (receita por categoria, top-5 cidades, receita mensal, distribuição de status). |
| `conversa.png` | Aba **Conversa**: pergunta em português respondida pelo agente com números calculados pelo código (tool-calling via OpenRouter). |
| `arquitetura.png` | Diagrama de arquitetura em imagem (export do [architecture.mermaid](../architecture.mermaid) — p/ renderizar, abra o arquivo em um editor com suporte a Mermaid ou em [mermaid.live](https://mermaid.live/) e exporte como PNG). |

## Como gerar (após rodar o app)

```bash
pip install -r requirements.txt
copy .env.example .env        # Windows; Linux/macOS: cp .env.example .env
# edite o .env com sua chave OPENROUTER_API_KEY (chat) — o painel funciona sem chave
streamlit run src/data_pilot/app.py
```

1. Com o app aberto, fotografe a aba **Painel** (janela inteira, sem editar) e salve como `painel.png` nesta pasta.
2. Configure a chave no `.env`, abra a aba **Conversa**, faça uma pergunta (ex.: “qual a receita total?”) e salve como `conversa.png`.
3. Exporte o Mermaid como `arquitetura.png` (opcional).

Os READMEs referenciam `docs/prints/painel.png`, `conversa.png` e `arquitetura.png`;
o importante é que os três prints existam aqui antes de publicar no GitHub.
