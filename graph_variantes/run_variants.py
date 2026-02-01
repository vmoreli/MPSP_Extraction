# -*- coding: utf-8 -*-
"""
Executa o experimento por documento:

- Chama cada prompt exatamente 1 vez (8 prompts)
- Guarda cache de outputs (pydantic válidos)
- Monta os 5 grafos a partir do cache
- Salva:
  - results_variants/prompts/<doc_id>/*.json
  - results_variants/graphs/<variant>/<doc_id>.json
- Imprime métricas (tempo e tokens) e total tokens
"""

import sys
from pathlib import Path
from typing import Dict, Any
import json

from pydantic import BaseModel

from graph_variantes.schemas_variants import (
    MapeamentoInqueritoOut,
    EnvolvidosOut,
    TudoOut,
)

from extraction_pipeline.schemas.extract_data_schemas import (
    ResumoProcesso,
    Inquerito,
    Vitimas,
    Suspeitos,
    Testemunhas,
)

from graph_variantes.prompts_variants import (
    prompt_mapeamento,
    prompt_inquerito_info,
    prompt_vitimas,
    prompt_suspeitos,
    prompt_testemunhas,
    prompt_mapeamento_inquerito,
    prompt_envolvidos_vst,
    prompt_tudo_em_um,
)

from graph_variantes.utils import (
    call_parse_with_retries,
    save_model_json,
    save_payload_json,
    STATS,
    total_tokens_llm,
    TOKENS_BY_DOC,   # <<< IMPORTA DO UTILS (não redefinir!)
)

from graph_variantes.build_graphs import build_variant_payloads


# =============================================================================
# EXECUÇÃO DOS PROMPTS (1x POR DOCUMENTO)
# =============================================================================
def run_all_prompts_once(doc_id: str, raw_text: str) -> Dict[str, Any]:
    """
    Executa os 8 prompts fixos exatamente uma vez por documento.
    """
    cache: Dict[str, Any] = {}

    # 1) mapeamento
    cache["mapeamento"] = call_parse_with_retries(
        "mapeamento",
        prompt_mapeamento.format(document=raw_text),
        ResumoProcesso,
        doc_id=doc_id,
    )

    # 2) inquerito
    cache["inquerito"] = call_parse_with_retries(
        "inquerito",
        prompt_inquerito_info.format(
            document=raw_text,
            classification=cache["mapeamento"].classificacao_crime.value,
        ),
        Inquerito,
        doc_id=doc_id,
    )

    # 3) vitimas
    vitimas_lista = cache["mapeamento"].pessoas_envolvidas.vitimas
    cache["vitimas"] = call_parse_with_retries(
        "vitimas",
        prompt_vitimas.format(
            document=raw_text,
            vitimas=", ".join(vitimas_lista),
        ),
        Vitimas,
        doc_id=doc_id,
    )

    # 4) suspeitos
    suspeitos_lista = cache["mapeamento"].pessoas_envolvidas.suspeitos_investigados
    cache["suspeitos"] = call_parse_with_retries(
        "suspeitos",
        prompt_suspeitos.format(
            document=raw_text,
            suspeitos=", ".join(suspeitos_lista),
        ),
        Suspeitos,
        doc_id=doc_id,
    )

    # 5) testemunhas
    testemunhas_lista = cache["mapeamento"].pessoas_envolvidas.testemunhas
    cache["testemunhas"] = call_parse_with_retries(
        "testemunhas",
        prompt_testemunhas.format(
            document=raw_text,
            testemunhas=", ".join(testemunhas_lista),
        ),
        Testemunhas,
        doc_id=doc_id,
    )

    # 6) mapeamento + inquerito
    cache["mapeamento_inquerito"] = call_parse_with_retries(
        "mapeamento_inquerito",
        prompt_mapeamento_inquerito.format(document=raw_text),
        MapeamentoInqueritoOut,
        doc_id=doc_id,
    )

    # 7) envolvidos (V/S/T)
    cache["envolvidos_vst"] = call_parse_with_retries(
        "envolvidos_vst",
        prompt_envolvidos_vst.format(document=raw_text),
        EnvolvidosOut,
        doc_id=doc_id,
    )

    # 8) tudo em um
    cache["tudo_em_um"] = call_parse_with_retries(
        "tudo_em_um",
        prompt_tudo_em_um.format(document=raw_text),
        TudoOut,
        doc_id=doc_id,
    )

    return cache


# =============================================================================
# SALVAMENTO
# =============================================================================
def save_prompts_cache(doc_id: str, cache: Dict[str, Any]) -> None:
    out_dir = Path("results_variants") / "prompts" / doc_id
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, model in cache.items():
        if isinstance(model, BaseModel):
            save_model_json(out_dir / f"{name}.json", model)


def save_graphs(doc_id: str, cache: Dict[str, Any]) -> None:
    variants = build_variant_payloads(cache)
    for variant_name, payload in variants.items():
        out_path = (
            Path("results_variants")
            / "graphs"
            / variant_name
            / f"{doc_id}.json"
        )
        save_payload_json(out_path, payload)
def save_token_costs(doc_id: str) -> None:
    out_dir = Path("results_variants") / "tokens"
    out_dir.mkdir(parents=True, exist_ok=True)

    prompt_tokens = TOKENS_BY_DOC.get(doc_id, {})

    payload = {
        "doc_id": doc_id,
        "total_tokens": sum(prompt_tokens.values()),
        "tokens_por_prompt": prompt_tokens,
    }

    with open(out_dir / f"{doc_id}.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)



# =============================================================================
# STATS
# =============================================================================
def print_stats(doc_id: str) -> None:
    print("\n===== STATS POR PROMPT =====")
    for name, s in STATS.items():
        print(
            f"{name:22s} | calls={s['calls']} | retries={s['retries']} | "
            f"time={s['seconds']:.2f}s | tokens={s['total_tokens']}"
        )

    print("\n===== TOKENS POR DOCUMENTO =====")
    for p, t in TOKENS_BY_DOC.get(doc_id, {}).items():
        print(f"{p:22s} : {t}")

    print("\n===== TOTAL TOKENS (LLM) =====")
    print(f"Total tokens consumidos: {total_tokens_llm()}")


# =============================================================================
# MAIN
# =============================================================================
def main():
    if len(sys.argv) < 2:
        raise SystemExit(
            "Uso: python -m graph_variantes.run_variants <caminho_arquivo.txt>"
        )

    input_path = Path(sys.argv[1])

    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")

    raw_text = input_path.read_text(encoding="utf-8", errors="ignore")

    # usa o nome da pasta que contém o arquivo
    doc_id = input_path.parent.name

    # =========================================================
    # CHECAGEM: já processado?
    # =========================================================
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    PROMPTS_DIR = PROJECT_ROOT / "results_variants" / "prompts" / doc_id

    if PROMPTS_DIR.exists():
        print(f"[SKIP] {doc_id} já tem outputs de prompts. Ignorando.")
        sys.exit(0)

    # =========================================================
    # EXECUÇÃO
    # =========================================================
    cache = run_all_prompts_once(doc_id, raw_text)

    save_prompts_cache(doc_id, cache)
    save_graphs(doc_id, cache)
    save_token_costs(doc_id)


    print_stats(doc_id)
    print("\nOK: outputs salvos em results_variants/.")


if __name__ == "__main__":
    main()
