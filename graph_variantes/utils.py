# -*- coding: utf-8 -*-
"""
Utils para o experimento:
- client Maritaca
- call_parse com métricas + retries
- IO (save json)
"""

import os
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Type

from dotenv import load_dotenv
from pydantic import BaseModel

from openai import OpenAI

from extraction_pipeline.schemas.extract_data_schemas import ClassificacaoCrime

load_dotenv()

DEFAULT_BASE_URL = os.getenv("MARITACA_BASE_URL", "https://chat.maritaca.ai/api")
DEFAULT_MODEL = os.getenv("MARITACA_MODEL", "sabia-2")

# Métricas globais (por execução)
STATS: Dict[str, Dict[str, Any]] = {}  # prompt_name -> {calls, seconds, prompt_tokens, completion_tokens, total_tokens}


def get_client() -> OpenAI:
    api_key = os.getenv("MARITACA_API_KEY")
    if not api_key:
        raise EnvironmentError("MARITACA_API_KEY não encontrada no ambiente/.env.")
    return OpenAI(api_key=api_key, base_url=DEFAULT_BASE_URL)




def _init_stats(prompt_name: str) -> None:
    if prompt_name not in STATS:
        STATS[prompt_name] = {
            "calls": 0,
            "seconds": 0.0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "retries": 0,
        }


def _accumulate(prompt_name: str, dt: float, usage: Optional[Any], retried: bool) -> None:
    _init_stats(prompt_name)
    s = STATS[prompt_name]
    s["calls"] += 1
    s["seconds"] += float(dt)
    if retried:
        s["retries"] += 1

    if usage:
        # usage pode ser objeto do SDK
        pt = int(getattr(usage, "prompt_tokens", 0) or 0)
        ct = int(getattr(usage, "completion_tokens", 0) or 0)
        tt = int(getattr(usage, "total_tokens", 0) or (pt + ct))
        s["prompt_tokens"] += pt
        s["completion_tokens"] += ct
        s["total_tokens"] += tt


def total_tokens_llm() -> int:
    return int(sum(v.get("total_tokens", 0) for v in STATS.values()))


def save_model_json(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(model.model_dump(mode="json"), f, ensure_ascii=False, indent=2)


def save_payload_json(path: Path, payload: Dict[str, Any]) -> None:
    """
    Salva payload de grafo (com vários BaseModel).
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    def _dump(x: Any):
        if isinstance(x, BaseModel):
            return x.model_dump(mode="json")
        return None if x is None else x

    with open(path, "w", encoding="utf-8") as f:
        json.dump({k: _dump(v) for k, v in payload.items()}, f, ensure_ascii=False, indent=2)


def _system_rules_base() -> str:
    # Isso NÃO altera seus prompts; só garante formato e diminui “texto fora do JSON”.
    return (
        "Responda APENAS em JSON válido, sem markdown, sem explicações.\n"
        "Siga estritamente o schema fornecido.\n"
    )


def _system_rules_retry() -> str:
    # Reforço para os erros mais comuns:
    # 1) enum de classificacao_crime
    # 2) regra armada -> arma_da_vitima
    enum_vals = [e.value for e in ClassificacaoCrime]
    return (
    "ATENÇÃO: sua resposta anterior foi REJEITADA pelo schema.\n\n"
    "ERRO CRÍTICO A EVITAR:\n"
    "- Se uma vítima tiver 'armada': true, o campo 'arma_da_vitima' "
    "DEVE ser preenchido com uma string NÃO vazia.\n\n"
    "Se a arma não estiver explicitamente indicada no texto, "
    "use EXATAMENTE o valor: \"Desconhecida\".\n\n"
    "NUNCA retorne:\n"
    "- armada=true com arma_da_vitima nula, vazia ou ausente.\n\n"
    "Responda APENAS em JSON válido conforme o schema."
)


def call_parse_once(
    client: OpenAI,
    prompt_text: str,
    schema: Type[BaseModel],
    model_name: str = DEFAULT_MODEL,
    extra_system: Optional[str] = None,
) -> BaseModel:
    """
    Uma chamada parse() com schema.
    """
    system_msg = _system_rules_base() + (extra_system or "")

    t0 = time.perf_counter()
    resp = client.beta.chat.completions.parse(
        model=model_name,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt_text},
        ],
        response_format=schema,
        temperature=0.0,
    )
    dt = time.perf_counter() - t0

    usage = getattr(resp, "usage", None)
    parsed = resp.choices[0].message.parsed
    return parsed, dt, usage


def call_parse_with_retries(
    prompt_name: str,
    prompt_text: str,
    schema: Type[BaseModel],
    model_name: str = DEFAULT_MODEL,
    max_retries: int = 2,
) -> BaseModel:
    """
    Faz parse() e, se falhar validação, tenta novamente (sem alterar prompt file).
    """
    client = get_client()

    # tentativa 1 (sem reforço extra)
    try:
        parsed, dt, usage = call_parse_once(client, prompt_text, schema, model_name=model_name)
        _accumulate(prompt_name, dt, usage, retried=False)
        return parsed
    except Exception as e1:
        # retries com reforço
        last_exc = e1
        for i in range(max_retries):
            try:
                parsed, dt, usage = call_parse_once(
                    client,
                    prompt_text,
                    schema,
                    model_name=model_name,
                    extra_system=_system_rules_retry(),
                )
                _accumulate(prompt_name, dt, usage, retried=True)
                return parsed
            except Exception as e2:
                last_exc = e2

        raise last_exc
