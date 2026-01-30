# -*- coding: utf-8 -*-
"""
Runner de variantes (LangGraph) usando apenas Maritaca.

Coloque este arquivo em:
  <repo_root>/graph_variantes/run_maritaca_variants.py

Requisitos:
- prompts combinados em: <repo_root>/graph_variantes/prompts_variants.py
  exportando:
    PROMPT_GUARDRAILS_PESSOAS
    prompt_mapeamento_inquerito
    prompt_envolvidos_vst
    prompt_tudo_em_um
    prompt_inquerito_e_envolvidos

Mudanças:
- `document` no output é o ID (nome da pasta pai do .txt, ex.: 130544000080820121)
- `raw_text` existe só internamente e NÃO é salvo no JSON final
- mede tempo por modelo por arquivo e total (e tokens best-effort)
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Any, Dict, Optional, List
from enum import Enum

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_core import ValidationError as PydanticCoreValidationError

from langgraph.graph import StateGraph, END
from langgraph.types import Command

# -----------------------------------------------------------------------------
# Garantir imports a partir da raiz do repo
# -----------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# -----------------------------------------------------------------------------
# Schemas do projeto
# -----------------------------------------------------------------------------
from extraction_pipeline.schemas.extract_data_schemas import (  # noqa: E402
    ResumoProcesso,
    Inquerito,
    Vitimas,
    Suspeitos,
    Testemunhas,
    ClassificacaoCrime,
)

# -----------------------------------------------------------------------------
# Prompts básicos do projeto
# -----------------------------------------------------------------------------
from extraction_pipeline.prompts.prompts import (  # noqa: E402
    prompt_mapeamento,
    prompt_inquerito_info,
    prompt_vitimas,
    prompt_suspeitos,
    prompt_testemunhas,
)

# -----------------------------------------------------------------------------
# Prompts combinados (arquivo separado em graph_variantes/)
# -----------------------------------------------------------------------------
GRAPH_VARIANTES_DIR = Path(__file__).resolve().parent
if str(GRAPH_VARIANTES_DIR) not in sys.path:
    sys.path.insert(0, str(GRAPH_VARIANTES_DIR))

from prompts_variants import (  # noqa: E402
    PROMPT_GUARDRAILS_PESSOAS,
    prompt_mapeamento_inquerito,
    prompt_envolvidos_vst,
    prompt_tudo_em_um,
    prompt_inquerito_e_envolvidos,
)

# -----------------------------------------------------------------------------
# Cliente Maritaca (OpenAI-compatible)
# -----------------------------------------------------------------------------
from openai import OpenAI  # noqa: E402

# -----------------------------------------------------------------------------
# Estado do grafo
# -----------------------------------------------------------------------------
class InqueritoTotal(BaseModel):
    document: str   # <-- ID (pasta)
    raw_text: str   # <-- texto bruto (não salvar no JSON)

    resumo_processo: Optional[ResumoProcesso] = None
    inquerito: Optional[Inquerito] = None
    vitimas: Optional[Vitimas] = None
    suspeitos: Optional[Suspeitos] = None
    testemunhas: Optional[Testemunhas] = None


# -----------------------------------------------------------------------------
# Schemas de saída para nós
# -----------------------------------------------------------------------------
class MapeamentoOut(BaseModel):
    resumo_processo: ResumoProcesso


class InqueritoOut(BaseModel):
    inquerito: Inquerito


class MapeamentoInqueritoOut(BaseModel):
    resumo_processo: ResumoProcesso
    inquerito: Inquerito


class EnvolvidosOut(BaseModel):
    vitimas: Optional[Vitimas] = None
    suspeitos: Optional[Suspeitos] = None
    testemunhas: Optional[Testemunhas] = None


class InqueritoEEnvolvidosOut(BaseModel):
    inquerito: Inquerito
    vitimas: Optional[Vitimas] = None
    suspeitos: Optional[Suspeitos] = None
    testemunhas: Optional[Testemunhas] = None


class TudoOut(BaseModel):
    resumo_processo: ResumoProcesso
    inquerito: Inquerito
    vitimas: Optional[Vitimas] = None
    suspeitos: Optional[Suspeitos] = None
    testemunhas: Optional[Testemunhas] = None


# -----------------------------------------------------------------------------
# STATS: tempo + tokens (best-effort)
# -----------------------------------------------------------------------------
CURRENT_VARIANT: str = "unknown"
CURRENT_DOC_ID: str = "unknown"

# stats por arquivo -> por modelo
FILE_STATS: Dict[str, Dict[str, Dict[str, float]]] = {}
# totals por modelo (soma de todos arquivos)
TOTAL_BY_MODEL: Dict[str, Dict[str, float]] = {}

def _ensure_model_slot(d: Dict[str, Dict[str, float]], model: str) -> None:
    d.setdefault(model, {"seconds": 0.0, "calls": 0.0, "prompt_tokens": 0.0, "completion_tokens": 0.0, "total_tokens": 0.0})

def _add_time_and_usage(doc_id: str, model: str, seconds: float, usage: Any) -> None:
    # por arquivo
    FILE_STATS.setdefault(doc_id, {})
    _ensure_model_slot(FILE_STATS[doc_id], model)
    FILE_STATS[doc_id][model]["seconds"] += float(seconds)
    FILE_STATS[doc_id][model]["calls"] += 1.0

    # total
    _ensure_model_slot(TOTAL_BY_MODEL, model)
    TOTAL_BY_MODEL[model]["seconds"] += float(seconds)
    TOTAL_BY_MODEL[model]["calls"] += 1.0

    if usage is None:
        return

    prompt = getattr(usage, "prompt_tokens", None)
    completion = getattr(usage, "completion_tokens", None)
    total = getattr(usage, "total_tokens", None)
    if isinstance(usage, dict):
        prompt = usage.get("prompt_tokens", prompt)
        completion = usage.get("completion_tokens", completion)
        total = usage.get("total_tokens", total)

    if prompt is None and completion is None and total is None:
        return

    FILE_STATS[doc_id][model]["prompt_tokens"] += float(prompt or 0)
    FILE_STATS[doc_id][model]["completion_tokens"] += float(completion or 0)
    FILE_STATS[doc_id][model]["total_tokens"] += float(total or 0)

    TOTAL_BY_MODEL[model]["prompt_tokens"] += float(prompt or 0)
    TOTAL_BY_MODEL[model]["completion_tokens"] += float(completion or 0)
    TOTAL_BY_MODEL[model]["total_tokens"] += float(total or 0)


# -----------------------------------------------------------------------------
# Maritaca caller com retry
# -----------------------------------------------------------------------------
def _get_client() -> OpenAI:
    api_key = os.getenv("MARITACA_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "A variável de ambiente 'MARITACA_API_KEY' não foi encontrada. "
            "Defina no ambiente (set MARITACA_API_KEY=...) ou em um .env na raiz do projeto."
        )
    base_url = os.getenv("MARITACA_BASE_URL", "https://chat.maritaca.ai/api")
    return OpenAI(api_key=api_key, base_url=base_url)


def _get_model() -> str:
    return os.getenv("MARITACA_MODEL") or os.getenv("MODEL") or "sabia-2"


def call_maritaca(
    raw_text: str,
    prompt_template: str,
    response_schema: type[BaseModel],
    *,
    format_kwargs: Optional[Dict[str, Any]] = None,
    max_retries: int = 2,
    retry_sleep_s: float = 0.6,
) -> BaseModel:
    """
    Chama Maritaca e valida/parsa para `response_schema`.

    Regra pedida:
    - Se `é_policial=true` e corporação não estiver no texto, preencher `corporacao_policial` com "não informado".
    """
    client = _get_client()
    base_model = _get_model()

    fmt = {"document": raw_text}
    if format_kwargs:
        fmt.update(format_kwargs)

    base_prompt = prompt_template.format(**fmt)

    system_msg = "Você extrai informações estruturadas e responde APENAS no formato exigido (JSON)."
    user_msg = base_prompt

    last_err: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        model_for_attempt = base_model
        t0 = time.perf_counter()
        try:
            resp = client.beta.chat.completions.parse(
                model=base_model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                response_format=response_schema,
                temperature=0,
            )
            dt = time.perf_counter() - t0

            # melhor modelo possível (se vier na resposta)
            model_for_attempt = getattr(resp, "model", None) or base_model
            _add_time_and_usage(CURRENT_DOC_ID, model_for_attempt, dt, getattr(resp, "usage", None))

            return resp.choices[0].message.parsed

        except (PydanticCoreValidationError, ValueError) as e:
            dt = time.perf_counter() - t0
            _add_time_and_usage(CURRENT_DOC_ID, model_for_attempt, dt, None)

            last_err = e
            if attempt >= max_retries:
                break

            user_msg = (
                base_prompt
                + "\n\n---\nATENÇÃO (correção obrigatória):\n"
                + "Sua resposta anterior NÃO validou no schema. Ajuste e responda novamente.\n"
                + "Regras de validação:\n"
                + "1) Se `é_policial=true`, então `corporacao_policial` deve estar preenchida. "
                + "Se o texto NÃO informar a corporação, preencha `corporacao_policial` com a string literal: \"não informado\".\n"
                + "2) Não use a string 'não informado' em campos gerais; use null/omita conforme o schema. "
                + "EXCEÇÃO: `corporacao_policial` pode receber \"não informado\" quando `é_policial=true`.\n"
                + "---\n"
            )
            time.sleep(retry_sleep_s)

        except Exception as e:
            dt = time.perf_counter() - t0
            _add_time_and_usage(CURRENT_DOC_ID, model_for_attempt, dt, None)

            last_err = e
            if attempt >= max_retries:
                break
            time.sleep(retry_sleep_s)

    raise RuntimeError(f"Falha ao obter resposta estruturada do Maritaca após retries: {last_err}")


# -----------------------------------------------------------------------------
# Utilitários
# -----------------------------------------------------------------------------
def _names_or_empty(xs: Optional[List[str]]) -> List[str]:
    return [x for x in (xs or []) if isinstance(x, str) and x.strip()]


def _serialize(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(v) for v in obj]
    return obj


def read_document(input_path: Path) -> str:
    if input_path.is_file():
        return input_path.read_text(encoding="utf-8", errors="ignore")

    if input_path.is_dir():
        parts = []
        for p in sorted(input_path.rglob("*.txt")):
            parts.append(p.read_text(encoding="utf-8", errors="ignore"))
        if not parts:
            raise FileNotFoundError(f"Nenhum .txt encontrado em: {input_path}")
        return "\n\n".join(parts)

    raise FileNotFoundError(f"Caminho inválido: {input_path}")


def make_doc_id(input_path: Path) -> str:
    """ID para `document` no output: pasta pai imediata do arquivo (ou o nome do dir)."""
    if input_path.is_file():
        return input_path.parent.name
    return input_path.name


def _clean_output_dict(out: Any) -> Any:
    """Remove raw_text do output final."""
    out_ser = _serialize(out)
    if isinstance(out_ser, dict):
        out_ser.pop("raw_text", None)
    return out_ser


# -----------------------------------------------------------------------------
# Nós básicos
# -----------------------------------------------------------------------------
def node_mapeamento(state: InqueritoTotal) -> Command:
    out = call_maritaca(state.raw_text, prompt_mapeamento, MapeamentoOut)
    goto = END if out.resumo_processo.classificacao_crime == ClassificacaoCrime.MORTE_CAUSAS_NATURAIS else "I"
    return Command(update={"resumo_processo": out.resumo_processo}, goto=goto)


def node_inquerito(state: InqueritoTotal) -> Command:
    classification = None
    if state.resumo_processo is not None:
        classification = state.resumo_processo.classificacao_crime.value

    out = call_maritaca(
        state.raw_text,
        prompt_inquerito_info,
        InqueritoOut,
        format_kwargs={"classification": classification},
    )

    vitimas = _names_or_empty(
        getattr(state.resumo_processo.pessoas_envolvidas, "vitimas", None) if state.resumo_processo else None
    )
    suspeitos = _names_or_empty(
        getattr(state.resumo_processo.pessoas_envolvidas, "suspeitos_investigados", None) if state.resumo_processo else None
    )
    testemunhas = _names_or_empty(
        getattr(state.resumo_processo.pessoas_envolvidas, "testemunhas", None) if state.resumo_processo else None
    )

    if vitimas:
        goto = "V"
    elif suspeitos:
        goto = "S"
    elif testemunhas:
        goto = "T"
    else:
        goto = END

    return Command(update={"inquerito": out.inquerito}, goto=goto)


def node_vitimas(state: InqueritoTotal) -> Command:
    vitimas_list = _names_or_empty(state.resumo_processo.pessoas_envolvidas.vitimas if state.resumo_processo else None)
    vitimas_str = "\n".join(vitimas_list)

    out = call_maritaca(
        state.raw_text,
        prompt_vitimas + "\n\n" + PROMPT_GUARDRAILS_PESSOAS,
        Vitimas,
        format_kwargs={"vitimas": vitimas_str},
    )

    suspeitos_list = _names_or_empty(
        state.resumo_processo.pessoas_envolvidas.suspeitos_investigados if state.resumo_processo else None
    )
    testemunhas_list = _names_or_empty(state.resumo_processo.pessoas_envolvidas.testemunhas if state.resumo_processo else None)

    goto = "S" if suspeitos_list else ("T" if testemunhas_list else END)
    return Command(update={"vitimas": out}, goto=goto)


def node_suspeitos(state: InqueritoTotal) -> Command:
    suspeitos_list = _names_or_empty(
        state.resumo_processo.pessoas_envolvidas.suspeitos_investigados if state.resumo_processo else None
    )
    suspeitos_str = "\n".join(suspeitos_list)

    out = call_maritaca(
        state.raw_text,
        prompt_suspeitos + "\n\n" + PROMPT_GUARDRAILS_PESSOAS,
        Suspeitos,
        format_kwargs={"suspeitos": suspeitos_str},
    )

    testemunhas_list = _names_or_empty(state.resumo_processo.pessoas_envolvidas.testemunhas if state.resumo_processo else None)
    goto = "T" if testemunhas_list else END
    return Command(update={"suspeitos": out}, goto=goto)


def node_testemunhas(state: InqueritoTotal) -> Command:
    testemunhas_list = _names_or_empty(state.resumo_processo.pessoas_envolvidas.testemunhas if state.resumo_processo else None)
    testemunhas_str = "\n".join(testemunhas_list)

    out = call_maritaca(
        state.raw_text,
        prompt_testemunhas + "\n\n" + PROMPT_GUARDRAILS_PESSOAS,
        Testemunhas,
        format_kwargs={"testemunhas": testemunhas_str},
    )

    return Command(update={"testemunhas": out}, goto=END)


# -----------------------------------------------------------------------------
# Nós combinados
# -----------------------------------------------------------------------------
def node_mapeamento_inquerito(state: InqueritoTotal) -> Command:
    out = call_maritaca(state.raw_text, prompt_mapeamento_inquerito, MapeamentoInqueritoOut)

    if out.resumo_processo.classificacao_crime == ClassificacaoCrime.MORTE_CAUSAS_NATURAIS:
        goto = END
    else:
        vitimas_list = _names_or_empty(out.resumo_processo.pessoas_envolvidas.vitimas)
        suspeitos_list = _names_or_empty(out.resumo_processo.pessoas_envolvidas.suspeitos_investigados)
        testemunhas_list = _names_or_empty(out.resumo_processo.pessoas_envolvidas.testemunhas)

        if vitimas_list:
            goto = "V"
        elif suspeitos_list:
            goto = "S"
        elif testemunhas_list:
            goto = "T"
        else:
            goto = END

    return Command(update={"resumo_processo": out.resumo_processo, "inquerito": out.inquerito}, goto=goto)


def node_envolvidos_vst(state: InqueritoTotal) -> Command:
    out = call_maritaca(state.raw_text, prompt_envolvidos_vst, EnvolvidosOut)
    return Command(update={"vitimas": out.vitimas, "suspeitos": out.suspeitos, "testemunhas": out.testemunhas}, goto=END)


def node_inquerito_e_envolvidos(state: InqueritoTotal) -> Command:
    out = call_maritaca(state.raw_text, prompt_inquerito_e_envolvidos, InqueritoEEnvolvidosOut)
    return Command(
        update={"inquerito": out.inquerito, "vitimas": out.vitimas, "suspeitos": out.suspeitos, "testemunhas": out.testemunhas},
        goto=END,
    )


def node_tudo_em_um(state: InqueritoTotal) -> Command:
    out = call_maritaca(state.raw_text, prompt_tudo_em_um, TudoOut)
    return Command(
        update={
            "resumo_processo": out.resumo_processo,
            "inquerito": out.inquerito,
            "vitimas": out.vitimas,
            "suspeitos": out.suspeitos,
            "testemunhas": out.testemunhas,
        },
        goto=END,
    )


# -----------------------------------------------------------------------------
# Variantes
# -----------------------------------------------------------------------------
VARIANTS = [
    "5_nodes",
    "4_nodes_MI_V_S_T",
    "3_nodes_M_I_VST",
    "2_nodes_MI_VST",
    "1_node_all",
]


def build_variant(name: str):
    g = StateGraph(InqueritoTotal)

    if name == "5_nodes":
        g.add_node("M", node_mapeamento)
        g.add_node("I", node_inquerito)
        g.add_node("V", node_vitimas)
        g.add_node("S", node_suspeitos)
        g.add_node("T", node_testemunhas)
        g.set_entry_point("M")

    elif name == "4_nodes_MI_V_S_T":
        g.add_node("MI", node_mapeamento_inquerito)
        g.add_node("V", node_vitimas)
        g.add_node("S", node_suspeitos)
        g.add_node("T", node_testemunhas)
        g.set_entry_point("MI")

    elif name == "3_nodes_M_I_VST":
        def node_inquerito_to_vst(state: InqueritoTotal) -> Command:
            cmd = node_inquerito(state)
            if cmd.goto == END:
                return cmd
            return Command(update=cmd.update, goto="VST")

        g.add_node("M", node_mapeamento)
        g.add_node("I", node_inquerito_to_vst)
        g.add_node("VST", node_envolvidos_vst)
        g.set_entry_point("M")

    elif name == "2_nodes_MI_VST":
        def node_mi_to_vst(state: InqueritoTotal) -> Command:
            cmd = node_mapeamento_inquerito(state)
            if cmd.goto == END:
                return cmd
            return Command(update=cmd.update, goto="VST")

        g.add_node("MI", node_mi_to_vst)
        g.add_node("VST", node_envolvidos_vst)
        g.set_entry_point("MI")

    elif name == "1_node_all":
        g.add_node("ALL", node_tudo_em_um)
        g.set_entry_point("ALL")

    else:
        raise ValueError(f"Variant desconhecida: {name}. Opções: {', '.join(VARIANTS)}")

    return g.compile()


# -----------------------------------------------------------------------------
# Impressão de stats
# -----------------------------------------------------------------------------
def _print_stats_for_doc(doc_id: str) -> None:
    print(f"\n=== STATS por modelo | arquivo {doc_id} ===")
    by_model = FILE_STATS.get(doc_id, {})
    if not by_model:
        print("- (sem dados)")
        return
    for model, u in sorted(by_model.items(), key=lambda kv: kv[0]):
        secs = u["seconds"]
        calls = int(u["calls"])
        tok_total = int(u["total_tokens"])
        print(f"- {model} | calls={calls} | seconds={secs:.2f} | total_tokens={tok_total}")


def _print_stats_totals() -> None:
    print("\n=== STATS por modelo | SOMA de todos os arquivos ===")
    if not TOTAL_BY_MODEL:
        print("- (sem dados)")
        return
    for model, u in sorted(TOTAL_BY_MODEL.items(), key=lambda kv: kv[0]):
        secs = u["seconds"]
        calls = int(u["calls"])
        tok_total = int(u["total_tokens"])
        print(f"- {model} | calls={calls} | seconds={secs:.2f} | total_tokens={tok_total}")


# -----------------------------------------------------------------------------
# Main (1 arquivo OU batch)
# -----------------------------------------------------------------------------
def main():
    load_dotenv(dotenv_path=REPO_ROOT / ".env", override=False)

    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", help="Arquivo .txt ou pasta contendo .txt (um inquérito)")
    group.add_argument("--batch_dir", help="Pasta com vários .txt (cada .txt vira um output)")

    parser.add_argument("--out_dir", default="results_variants", help="Pasta de saída (pode ser caminho absoluto no Windows)")
    parser.add_argument("--variant", default="all", help="all ou um nome em: " + ", ".join(VARIANTS))
    parser.add_argument("--print_stats", action="store_true", help="Imprime tempo e tokens (best-effort) por modelo")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    variants_to_run = VARIANTS if args.variant == "all" else [args.variant]

    # inputs
    inputs: List[Path] = []
    if args.batch_dir:
        batch = Path(args.batch_dir)
        if not batch.exists():
            raise FileNotFoundError(f"batch_dir não existe: {batch}")
        inputs = sorted(batch.rglob("*.txt"))
        if not inputs:
            raise FileNotFoundError(f"Nenhum .txt encontrado em: {batch}")
    else:
        ip = Path(args.input)
        if not ip.exists():
            raise FileNotFoundError(f"input não existe: {ip}")
        inputs = [ip]

    for input_path in inputs:
        raw_text = read_document(input_path)
        doc_id = make_doc_id(input_path)

        global CURRENT_DOC_ID
        CURRENT_DOC_ID = doc_id

        for vname in variants_to_run:
            global CURRENT_VARIANT
            CURRENT_VARIANT = vname

            pipe = build_variant(vname)

            try:
                out = pipe.invoke({"document": doc_id, "raw_text": raw_text})
            except Exception as e:
                out = {"document": doc_id, "error": f"{type(e).__name__}: {e}"}

            out_path = out_dir / vname
            out_path.mkdir(parents=True, exist_ok=True)
            out_file = out_path / f"{doc_id}.json"

            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(_clean_output_dict(out), f, ensure_ascii=False, indent=2)

            print(f"[OK] {vname} -> {out_file}")

        if args.print_stats:
            _print_stats_for_doc(doc_id)

    if args.print_stats and len(inputs) > 1:
        _print_stats_totals()


if __name__ == "__main__":
    main()
