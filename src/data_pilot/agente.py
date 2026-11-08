"""Agente conversacional do Data Pilot via OpenRouter (Fase 4).

Regra central: o Python calcula, o LLM só explica. O modelo nunca recebe a
planilha crua: ele escolhe uma ferramenta (tool-calling), o código executa
localmente via `ferramentas.executar_ferramenta` e o número volta ao modelo,
que só formata a frase final. Sem SDK de agentes (LangChain etc.): apenas
`requests` direto no endpoint OpenAI-compatible do OpenRouter.

Configuração via variáveis de ambiente / arquivo `.env` (python-dotenv):
- `OPENROUTER_API_KEY`: chave do OpenRouter (nunca commite; só no `.env` local).
- `OPENROUTER_MODEL`: default `nvidia/nemotron-3.5-lightning:free`.
- `OPENROUTER_BASE_URL`: default `https://openrouter.ai/api/v1`.

Descoberta do modelo gratuito com tool-calling:
  - Consulte `GET https://openrouter.ai/api/v1/models` e procured modelos
    cujo campo `supported_parameters` inclui `tools` e `tool_choice`.
  - O default acima (`nvidia/nemotron-3.5-lightning:free`) foi confirmado
    dessa lista em 2026-11-08 (ver `.env.example`).
  - Se `OPENROUTER_MODEL=openrouter/free` (pseudo-modelo "qualquer modelo
    grátis"), chama-se a API uma vez; se a resposta indicar modelo inválido
    ou sem tool-calling, cai-se para o default gratuito acima. Em geral,
    prefira fixar um modelo `:free` específico no `.env`.
"""

from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv

from data_pilot.ferramentas import TOOLS, executar_ferramenta

# Carrega o `.env` do projeto, se existir (sem sobrescrever o ambiente atual).
load_dotenv()

# Defaults (nunca hardcode chave aqui).
MODELO_PADRAO = "nvidia/nemotron-3.5-lightning:free"
BASE_URL_PADRAO = "https://openrouter.ai/api/v1"

# Instrução de sistema: reforça a divisão de tarefas (Python calcula, IA explica).
INSTRUCAO_SISTEMA = (
    "Você é Data Pilot. Python calcula, você só explica. "
    "Use ferramentas para números. Não assuma números: "
    "se precisar de qualquer valor, chame a ferramenta correspondente. "
    "Se não houver pedidos/categorias para o filtro, diga isso explicitamente."
)

_MAX_ITERACOES = 10


def _get_config() -> tuple[str, str, str]:
    """Lê (api_key, modelo, base_url) do ambiente, com fallbacks documentados."""
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    modelo = os.getenv("OPENROUTER_MODEL", MODELO_PADRAO).strip() or MODELO_PADRAO
    base_url = os.getenv("OPENROUTER_BASE_URL", BASE_URL_PADRAO).strip() or BASE_URL_PADRAO
    return api_key, modelo, base_url


def chamar_openrouter(
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    api_key: str = "",
    base_url: str = BASE_URL_PADRAO,
) -> dict[str, Any]:
    """Chama `POST {base_url}/chat/completions` (OpenAI-compatible).

    Args:
        model: nome do modelo no OpenRouter.
        messages: mensagens no formato OpenAI (system/user/assistant/tool).
        tools: descritores de ferramentas (default None = sem ferramentas).
        api_key: chave Bearer (lida do `.env` pelo chamador quando vazio).
        base_url: base da API (default OpenRouter).

    Returns:
        Dict com `content` (str, pode ser "" se houver só tool_calls) e
        `tool_calls` (lista do modelo; vazia quando não chamou ferramenta).

    Raises:
        RuntimeError: se a chave faltar, a rede falhar, o HTTP não for 2xx
            ou o JSON não tiver o formato esperado.
    """
    if not api_key:
        # Tenta o ambiente uma última vez (ex.: chamada direta sem key explícita).
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY não definida. "
            "Copie .env.example para .env e preencha."
        )

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "tool_choice": "auto",
    }
    if tools:
        payload["tools"] = tools

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/KelvinOliveiraCode/data-pilot",
        "X-Title": "Data Pilot",
        "Content-Type": "application/json",
    }
    url = base_url.rstrip("/") + "/chat/completions"
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
    except requests.RequestException as exc:
        raise RuntimeError(f"Falha de rede ao chamar o OpenRouter: {exc}") from exc

    if resp.status_code < 200 or resp.status_code >= 300:
        # Corpo pode conter {"error": {"message": ...}}: expõe para debug no app.
        detalhe = resp.text[:1000]
        raise RuntimeError(f"OpenRouter HTTP {resp.status_code}: {detalhe}")

    try:
        data = resp.json()
    except ValueError as exc:
        raise RuntimeError(f"Resposta não-JSON do OpenRouter: {resp.text[:500]}") from exc

    try:
        message = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Resposta inesperada do OpenRouter: {json.dumps(data)[:1000]}") from exc

    content = message.get("content") or ""
    tool_calls = message.get("tool_calls") or []
    return {"content": content, "tool_calls": tool_calls}


def _resolver_chave(api_key_override: str | None = None) -> str:
    """Resolve a chave: override do session_state (input da UI) > env.

    Nunca nunca retorna valores de outra fonte nem loga a chave.
    Valores vazios/None significam "sem chave".
    """
    if api_key_override is not None and str(api_key_override).strip():
        return str(api_key_override).strip()
    return os.getenv("OPENROUTER_API_KEY", "").strip()


def conversar(
    df: pd.DataFrame,
    pergunta: str,
    historico: list[dict[str, Any]] | None = None,
    modelo: str | None = None,
    api_key: str | None = None,
) -> str:
    """Conversa com o Data Pilot: loop tool-calling até a resposta final.

    Fluxo (até 10 rodadas):
    1. Monta as mensagens: sistema + histórico + pergunta nova.
    2. Chama o modelo com TOOLS; se ele pediu ferramentas, executa cada
       uma localmente e injeta o resultado como mensagem `role="tool"`.
    3. Se não pediu ferramenta, retorna o `content` como resposta final.

    Args:
        df: DataFrame limpo com os dados.
        pergunta: texto da pergunta do usuário.
        historico: mensagens anteriores no formato OpenAI (opcional).
        modelo: override do modelo (opcional; default vem do ambiente).

    Returns:
        Resposta final em texto (sempre str, mesmo em erro de API : 
        erros são devolvidos como texto explicativo, sem exceção).
    """
    api_key_cfg, modelo_env, base_url = _get_config()
    api_key = _resolver_chave(api_key)
    if not api_key:
        api_key = api_key_cfg  # fallback duplo (compat: _get_config já lia o env)
    modelo_usado = modelo or modelo_env

    if not api_key:
        return (
            "⚠️ Para conversar, configure `OPENROUTER_API_KEY` no arquivo `.env` "
            "(copie de `.env.example`) ou informe sua chave no campo abaixo. "
            "O Painel funciona sem chave; o Chat precisa dela."
        )

    mensagens: list[dict[str, Any]] = [{"role": "system", "content": INSTRUCAO_SISTEMA}]
    if historico:
        mensagens.extend(dict(m) for m in historico)
    mensagens.append({"role": "user", "content": pergunta})

    try:
        for _ in range(_MAX_ITERACOES):
            resposta = chamar_openrouter(
                model=modelo_usado,
                messages=mensagens,
                tools=TOOLS,
                api_key=api_key,
                base_url=base_url,
            )

            tool_calls = resposta.get("tool_calls") or []
            if not tool_calls:
                # Resposta final: o modelo já explica com os números das ferramentas.
                return str(resposta.get("content") or "Sem resposta do modelo.").strip()

            # Registra a mensagem do assistente com as tool_calls (protocolo OpenAI).
            mensagens.append(
                {
                    "role": "assistant",
                    "content": resposta.get("content") or None,
                    "tool_calls": tool_calls,
                }
            )

            # Executa cada ferramenta localmente e injeta como mensagem tool.
            for chamada in tool_calls:
                nome = chamada.get("function", {}).get("name", "")
                args_raw = chamada.get("function", {}).get("arguments", "{}")
                try:
                    if isinstance(args_raw, str):
                        args = json.loads(args_raw)
                    else:
                        args = dict(args_raw or {})
                except (json.JSONDecodeError, TypeError):
                    args = {}
                resultado = executar_ferramenta(nome, args, df)
                print(f"[tool] {nome} args={args} -> {resultado}")
                mensagens.append(
                    {
                        "role": "tool",
                        "tool_call_id": chamada.get("id", ""),
                        "name": nome,
                        "content": json.dumps(resultado, ensure_ascii=False, default=str),
                    }
                )
    except RuntimeError as exc:
        # Fallback de modelo livre: se o usuário usou o pseudo-modelo
        # `openrouter/free` e ele falhou, tenta o default gratuito.
        if modelo_usado == "openrouter/free" and modelo_usado != MODELO_PADRAO:
            return conversar(df, pergunta, historico=historico, modelo=MODELO_PADRAO)
        return f"⚠️ Erro ao falar com o modelo ({modelo_usado}): {exc}"

    return (
        "Limite de 10 rodadas de ferramentas atingido. "
        "Reformule a pergunta de forma mais simples."
    )
