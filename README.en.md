# data-pilot

<div align="center">

**English** · [Português (Brasil)](README.md)

</div>

[![Python 3](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/) [![pandas](https://img.shields.io/badge/pandas-150458?style=flat-square&logo=pandas)](https://pandas.pydata.org/) [![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io/) [![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=flat-square&logo=pytest)](https://docs.pytest.org/) [![MIT License](https://img.shields.io/badge/License-MIT-f4c430?style=flat-square)](LICENSE)

### Intelligent Data Analysis with AI Agents — a sales dashboard that talks

---

## What it is

**Data Pilot**: a Python sales dashboard that also *chats* with you in natural language. You ask a question and an AI agent answers using **only numbers computed by your own code** (pandas) — the AI explains; it never invents.

Layered architecture, no agent framework:
1. **Data** (`pandas`): cleans `sales.csv` and produces `sales_clean.csv`;
2. **Metrics**: one Python function per business question, always over completed orders;
3. **Dashboard** (`Streamlit` + `Plotly`): KPIs, monthly revenue chart and Top-5 cities;
4. **Chat** (`OpenRouter` + free model): the model *itself* picks which function to call (tool calling).

---

## Quick Start

```bash
git clone https://github.com/KelvinOliveiraCode/data-pilot.git
cd data-pilot
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows; Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env       # or: cp .env.example .env
# edit .env with your OpenRouter key and the free model
streamlit run app.py
```

> Without a key, the **Dashboard** works normally and **Chat** tells you how to configure it. Without `data/sales.csv`, the app generates a deterministic synthetic CSV (fallback) and warns.

---

## How it works

Core rule: **Python computes; the AI only explains.**

- The model never sees the raw spreadsheet — only numeric results produced by a function.
- Each metric function (`calcular_receita_total`, `calcular_ticket_medio`, …) is registered as a **tool** (name, description, parameters).
- The LLM picks which tool to call; the code executes it locally and returns the number; the model only formats the final sentence.
- The chat log shows **which function ran, with which parameters and which result** — proof the numbers are real.

---

## Capabilities

| Capability | Description |
|------------|-------------|
| Data cleaning | Dates parsed, statuses normalized, duplicates removed, `receita` column; writes `sales_clean.csv` with `;` separator and `,` decimal |
| Business metrics | Total revenue, orders, average ticket, unique customers, cancellation rate — always over completed orders |
| Interactive dashboard | Cards (KPIs), category filter, monthly revenue chart (Plotly) |
| Chat with tools | PT questions → model calls the right function (tool calling) → answer with code-computed numbers |
| Free model | OpenRouter (`:free`) with tool-calling support, key in `.env` |
| Tests | `pytest` covering cleaning, metrics, dashboard ≡ chat parity and tool contracts |

---

## Project structure

```
data-pilot/
├── app.py
├── .env.example
├── requirements.txt
├── pyproject.toml
├── data/
│   └── sales.csv
├── src/data_pilot/
│   ├── dados.py
│   ├── metricas.py
│   ├── ferramentas.py
│   ├── agente.py
│   ├── graficos.py
│   ├── painel.py
│   └── conversa.py
├── tests/
│   ├── test_dados.py
│   ├── test_metricas.py
│   ├── test_ferramentas.py
│   └── test_painel.py
└── docs/prints/
    ├── painel.png
    ├── conversa.png
    └── grafico_meta.png
```

---

## Screenshots

### Dashboard

See `docs/prints/painel.png`.

### Chat answered with a tool call

See `docs/prints/conversa.png`.

### Chart (improvement: Top-5 cities)

See `docs/prints/grafico_meta.png`.

---

## Model tools (tool calling)

| Function | What it computes | Parameters |
|----------|------------------|------------|
| `calcular_receita_total` | Revenue from completed orders | `categoria` (optional) |
| `calcular_quantidade_pedidos` | Number of completed orders | `categoria` (optional) |
| `calcular_ticket_medio` | Revenue ÷ orders | `categoria` (optional) |
| `calcular_clientes_unicos` | Distinct customers with a completed order | `categoria` (optional) |
| `calcular_taxa_cancelamento` | Cancelled ÷ total | `categoria` (optional) |
| `calcular_receita_media_por_cliente` | Revenue ÷ unique customers | `categoria` (optional) |
| `calcular_receita_por_cidade` | Top-5 cities by revenue | — |

---

## Chosen improvement

> **New metric + new chart + tool with a date range**: average revenue per customer, chart of the top-5 selling cities, and a tool accepting a period (`data_inicio`/`data_fim`) — all computed in code and answered in chat.

---

## FAQ

<details>
<summary><strong>Where is the data?</strong></summary>

In `data/sales.csv` (challenge sales spreadsheet). The app cleans it with pandas and produces `data/sales_clean.csv`.
</details>

<details>
<summary><strong>Do I need an API key?</strong></summary>

Only for Chat. Create an OpenRouter account and set `OPENROUTER_API_KEY` in `.env` (copy from `.env.example`). The Dashboard works without a key.
</details>

<details>
<summary><strong>How do I test?</strong></summary>

```bash
pytest -q
ruff check .
```
</details>

<details>
<summary><strong>Can I use this in production?</strong></summary>

This is a **study/portfolio project**. Harden it (secrets, rate-limit, observability) before any production use.
</details>

---

## Documentation

- **Source Code** ,  Browse the `src/` directory for implementation details
- **API Reference** ,  Inline docstrings + type hints
- **Architecture Diagram** ,  See [architecture.mermaid](docs/architecture.mermaid) (if present)
- **Changelog** ,  [CHANGELOG.md](CHANGELOG.md) (if present)
- **Contributing** ,  [CONTRIBUTING.md](CONTRIBUTING.md) (if present)

## License

[MIT](LICENSE) ,  Kelvin Oliveira

---

<div align="center">

**Built with** · Python 3 + pandas + Streamlit + Plotly + OpenRouter

**Author** · Kelvin Oliveira · Portfolio

</div>
