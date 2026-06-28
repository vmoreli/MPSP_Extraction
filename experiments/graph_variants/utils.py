# -*- coding: utf-8 -*-
import json
import time
import os
from pathlib import Path
from typing import Any, Dict, Optional, Type, Tuple

from pydantic import BaseModel
from openai import OpenAI
from google import genai

# Importação dos schemas para evitar NameError na normalização
from extraction_pipeline.schemas.extract_data_schemas import Vitimas, Suspeitos, Testemunhas

MODEL_BY_PROVIDER = {
    "gemini": "gemini-1.5-flash", # Corrigido de 2.5 para 1.5
    "maritaca": "sabia-3.1",
}

DEFAULT_PROVIDER = "maritaca"
DEFAULT_BASE_URL = os.getenv("MARITACA_BASE_URL", "https://chat.maritaca.ai/api")

STATS: Dict[str, Dict[str, Any]] = {}
TOKENS_BY_DOC: Dict[str, Dict[str, int]] = {}

def resolve_model_name(provider: str) -> str:
    return MODEL_BY_PROVIDER.get(provider.lower(), "sabia-3.1")

def _accumulate(prompt_name: str, dt: float, usage: Optional[Any], retried: bool, doc_id: str) -> None:
    if prompt_name not in STATS:
        STATS[prompt_name] = {
            "calls": 0,
            "seconds": 0.0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "retries": 0,
        }

    s = STATS[prompt_name]
    s["calls"] += 1
    s["seconds"] += float(dt)
    if retried:
        s["retries"] += 1

    if not usage:
        return

    pt = int(getattr(usage, "prompt_tokens", 0) or 0)
    ct = int(getattr(usage, "completion_tokens", 0) or 0)
    tt = int(getattr(usage, "total_tokens", 0) or (pt + ct))

    doc_stats = TOKENS_BY_DOC.setdefault(doc_id, {})
    doc_stats[prompt_name] = doc_stats.get(prompt_name, 0) + tt

def print_stats(doc_id: str):
    """Exibe o resumo de tokens e tempo para o documento processado."""
    print(f"\n=== Estatísticas de uso (doc: {doc_id}) ===")

    doc_tokens = TOKENS_BY_DOC.get(doc_id, {})
    total_doc_tokens = sum(doc_tokens.values())

    print(f"Total de tokens no documento: {total_doc_tokens}")

    for prompt_name, tokens in doc_tokens.items():
        print(f" - {prompt_name}: {tokens} tokens")

    print("========================================\n")
    
def save_token_stats(doc_id: str, out_dir: Path) -> None:
    """
    Salva o uso de tokens por prompt para um documento em JSON.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "doc_id": doc_id,
        "total_tokens": sum(TOKENS_BY_DOC.get(doc_id, {}).values()),
        "tokens_por_prompt": TOKENS_BY_DOC.get(doc_id, {}),
    }

    path = out_dir / f"{doc_id}_tokens.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def create_client(provider: str, api_key: str):
    provider = provider.lower()
    if provider == "maritaca":
        return OpenAI(api_key=api_key, base_url=DEFAULT_BASE_URL)
    elif provider == "gemini":
        return genai.Client(api_key=api_key)
    raise ValueError(f"Provider desconhecido: {provider}")

def call_parse_once(client: Any, prompt_text: str, schema: Type[BaseModel], model_name: str, provider: str) -> Tuple[BaseModel, float, Optional[Any]]:
    schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)
    system_msg = f"Siga EXATAMENTE este JSON Schema:\n{schema_json}"
    t0 = time.perf_counter()

    if provider == "maritaca":
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt_text}],
            temperature=0.0
        )
        content = resp.choices[0].message.content
        usage = resp.usage
    else: # Gemini
        resp = client.models.generate_content(model=model_name, contents=prompt_text, config={'response_mime_type': 'application/json', 'response_schema': schema})
        content = resp.text
        usage = getattr(resp, "usage_metadata", None)

    dt = time.perf_counter() - t0
    
    # Limpeza de Markdown se houver
    if content.startswith("```"):
        content = content.strip("`").replace("json", "", 1).strip()
    
    parsed = schema.model_validate_json(content)
    return parsed, dt, usage

def call_parse_with_retries(*, prompt_name: str, prompt_text: str, schema: Type[BaseModel], doc_id: str, client: Any, provider: str, max_retries: int = 1) -> BaseModel:
    model_name = resolve_model_name(provider)
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            parsed, dt, usage = call_parse_once(client, prompt_text, schema, model_name, provider)
            _accumulate(prompt_name, dt, usage, (attempt > 0), doc_id)
            return parsed
        except Exception as e:
            last_exc = e
            if attempt < max_retries:
                time.sleep(2)
    raise last_exc

def save_model_json(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(model.model_dump(mode="json"), f, ensure_ascii=False, indent=2)

def save_payload_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({k: (v.model_dump(mode="json") if isinstance(v, BaseModel) else v) for k, v in payload.items()}, f, ensure_ascii=False, indent=2)