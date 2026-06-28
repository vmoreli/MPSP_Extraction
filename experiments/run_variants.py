import sys
from pathlib import Path
from typing import Dict, Any
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
from graph_variantes.prompts_variants import *
from graph_variantes.utils import (
    call_parse_with_retries,
    save_model_json,
    save_payload_json,
    print_stats,
    create_client,
    save_token_stats,
)
from graph_variantes.build_graphs import build_variant_payloads


def run_all_prompts_once(
    doc_id: str, raw_text: str, client: Any, provider: str
) -> Dict[str, Any]:

    # Cache inicializado (essencial)
    cache: Dict[str, Any] = {
        "envolvidos_vst": None,
        "tudo_em_um": None,
        "mapeamento": None,
        "inquerito": None,
        "vitimas": None,
        "suspeitos": None,
        "testemunhas": None,
        "mapeamento_inquerito": None,
    }

    common_kwargs = {"doc_id": doc_id, "client": client, "provider": provider}

    cache["envolvidos_vst"] = call_parse_with_retries(
        prompt_name="envolvidos_vst",
        prompt_text=prompt_envolvidos_vst.replace("{document}", raw_text),
        schema=EnvolvidosOut,
        **common_kwargs,
    )

    cache["tudo_em_um"] = call_parse_with_retries(
        prompt_name="tudo_em_um",
        prompt_text=prompt_tudo_em_um.replace("{document}", raw_text),
        schema=TudoOut,
        **common_kwargs,
    )

    cache["mapeamento"] = call_parse_with_retries(
        prompt_name="mapeamento",
        prompt_text=prompt_mapeamento.replace("{document}", raw_text),
        schema=ResumoProcesso,
        **common_kwargs,
    )

    classif = (
        cache["mapeamento"].classificacao_crime.value
        if cache["mapeamento"] and cache["mapeamento"].classificacao_crime
        else "Desconhecido"
    )

    cache["inquerito"] = call_parse_with_retries(
        prompt_name="inquerito",
        prompt_text=prompt_inquerito_info
        .replace("{document}", raw_text)
        .replace("{classification}", classif),
        schema=Inquerito,
        **common_kwargs,
    )

    pessoas = cache["mapeamento"].pessoas_envolvidas if cache["mapeamento"] else None

    if pessoas and pessoas.vitimas:
        cache["vitimas"] = call_parse_with_retries(
            prompt_name="vitimas",
            prompt_text=prompt_vitimas
            .replace("{document}", raw_text)
            .replace("{vitimas}", ", ".join(pessoas.vitimas)),
            schema=Vitimas,
            **common_kwargs,
        )

    if pessoas and pessoas.suspeitos_investigados:
        cache["suspeitos"] = call_parse_with_retries(
            prompt_name="suspeitos",
            prompt_text=prompt_suspeitos
            .replace("{document}", raw_text)
            .replace("{suspeitos}", ", ".join(pessoas.suspeitos_investigados)),
            schema=Suspeitos,
            **common_kwargs,
        )

    if pessoas and pessoas.testemunhas:
        cache["testemunhas"] = call_parse_with_retries(
            prompt_name="testemunhas",
            prompt_text=prompt_testemunhas
            .replace("{document}", raw_text)
            .replace("{testemunhas}", ", ".join(pessoas.testemunhas)),
            schema=Testemunhas,
            **common_kwargs,
        )

    cache["mapeamento_inquerito"] = call_parse_with_retries(
        prompt_name="mapeamento_inquerito",
        prompt_text=prompt_mapeamento_inquerito.replace("{document}", raw_text),
        schema=MapeamentoInqueritoOut,
        **common_kwargs,
    )

    return cache


def main():
    if len(sys.argv) < 4:
        raise SystemExit(
            "Uso: python -m graph_variantes.run_variants <arquivo.txt> <provider> <api_key>"
        )

    input_path = Path(sys.argv[1])
    provider = sys.argv[2]
    api_key = sys.argv[3]

    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")

    raw_text = input_path.read_text(encoding="utf-8", errors="ignore")
    doc_id = input_path.parent.name

    final_output = Path("results_variants") / "graphs" / "5_nodes" / f"{doc_id}.json"
    if final_output.exists():
        print(f"[SKIP] {doc_id} já processado anteriormente.")
        return

    client = create_client(provider, api_key)
    cache = run_all_prompts_once(doc_id, raw_text, client, provider)

    out_dir = Path("results_variants") / "prompts" / doc_id
    for name, model in cache.items():
        if isinstance(model, BaseModel):
            save_model_json(out_dir / f"{name}.json", model)

    variants = build_variant_payloads(cache)
    for v_name, payload in variants.items():
        save_payload_json(
            Path("results_variants") / "graphs" / v_name / f"{doc_id}.json",
            payload,
        )

    print_stats(doc_id)

    save_token_stats(
    doc_id,
    Path("results_variants") / "tokens"
    )


if __name__ == "__main__":
    main()