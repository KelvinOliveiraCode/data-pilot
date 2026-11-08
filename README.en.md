# data-pilot

<div align="center">

**English** · [Português (Brasil)](README.md)

</div>

[![Python 3](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/) [![pandas](https://img.shields.io/badge/pandas-150458?style=flat-square&logo=pandas)](https://pandas.pydata.org/) [![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io/) [![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=flat-square&logo=plotly&logoColor=white)](https://plotly.com/) [![OpenRouter](https://img.shields.io/badge/OpenRouter-8B5CF6?style=flat-square)](https://openrouter.ai/) [![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=flat-square&logo=pytest)](https://docs.pytest.org/) [![MIT License](https://img.shields.io/badge/License-MIT-f4c430?style=flat-square)](LICENSE)

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
# or, installing the package with the `data-pilot` entry point:
pip install -e .
copy .env.example .env       # or: cp .env.example .env
# edit .env with your OpenRouter key (OPENROUTER_API_KEY) and the free model
#   OPENROUTER_MODEL=nvidia/nemotron-3.5-lightning:free
streamlit run src/data_pilot/app.py
# or, after `pip install -e .`:
data-pilot
```

> Without a key, the **Dashboard** works normally and **Chat** tells you how to configure it. Without `data/sales.csv`, the app generates a deterministic synthetic CSV (fallback) and warns.
>
> Data source: `data/sales.csv` (challenge sales spreadsheet; separator `;` or `,`). The code cleans it with pandas (`dados.py` → `carregar_dados`), deduplicates by `pedido_id` and produces `data/sales_clean.csv` (gitignored).

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
| Free model | OpenRouter (`nvidia/nemotron-3.5-lightning:free`) with tool-calling support, key in `.env` |
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
│   └── test_ferramentas.py
└── docs/prints/
    ├── painel.png
    ├── conversa.png
    └── arquitetura.png
```

> Diagram source: [docs/architecture.mermaid](docs/architecture.mermaid) (flow: dados.py → metricas.py → painel.py/graficos.py → agente.py/ferramentas.py).

---

## Screenshots

### Dashboard

See `docs/prints/painel.png`.

### Chat answered with a tool call

See `docs/prints/conversa.png`.

### Architecture

See `docs/prints/arquitetura.png`.

> Screenshots are completed after running the app; instructions in `docs/prints/README.md`.
> Diagram source: [docs/architecture.mermaid](docs/architecture.mermaid).

---

## Model tools (tool calling)

The model calls **snake_case names** (defined in `src/data_pilot/ferramentas.py`, `TOOLS`); the
`calcular_*` are the internal functions in `metricas.py` they dispatch to.

| Name (tool) | Internal function | What it computes | Parameters |
|--------|---------------|------------|------------|
| `receita_total` | `calcular_receita_total` | Revenue from completed orders | `categoria` (optional) |
| `pedidos_concluidos` | `calcular_pedidos_concluidos` | Number of completed orders | `categoria` (optional) |
| `ticket_medio` | `calcular_ticket_medio` | Revenue ÷ orders | `categoria` (optional) |
| `clientes_unicos` | `calcular_clientes_unicos` | Distinct customers with a completed order | `categoria` (optional) |
| `taxa_cancelamento` | `calcular_taxa_cancelamento` | Cancelled ÷ total (0–100 %) | `categoria` (optional) |
| `receita_media_por_cliente` | `calcular_receita_media_por_cliente` | Revenue ÷ unique customers | `categoria` (optional) |
| `top5_cidades_receita` | `calcular_top5_cidades_receita` | Top-5 cities by revenue | — |
| `filtrar_periodo` | `filtrar_periodo` | Records filtered by period | `data_inicio`/`data_fim`/`categoria` (optional) |

---

## Chosen improvement

> **New metric + new chart + tool with a date range**: average revenue per customer, top-5 cities by revenue (chart of the 5 best-selling cities), and a tool accepting a period/filter by period (`data_inicio`/`data_fim`) — all computed in code and answered in chat.

---

## DIO challenge project

Project developed in the context of a [DIO (Digital Innovation One)](https://www.dio.me/) challenge
— hands-on practice of agentic coding and data analysis with Python: a sales dashboard that talks,
with code as the numeric source of truth (Python computes; the AI only explains).

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

- **Source Code** — Browse the `src/` directory for implementation details
- **API Reference** — Inline docstrings + type hints
- **Architecture Diagram** — See [architecture.mermaid](docs/architecture.mermaid)
- **Changelog** — [CHANGELOG.md](CHANGELOG.md) (if present)
- **Contributing** — [CONTRIBUTING.md](CONTRIBUTING.md) (if present)

## License

[MIT](LICENSE) · Kelvin Oliveira

---

<div align="center">

**Built with** · Python 3 + pandas + Streamlit + Plotly + OpenRouter

**Author** · Kelvin Oliveira · Portfolio

</div>
