# build_graphs.py
from pydantic import BaseModel
from typing import Any, Dict, Optional
def safe_dump(model):
    """
    Converte um modelo Pydantic num dicionário. 
    Se o modelo for None, retorna um dicionário vazio ou None conforme a necessidade.
    """
    if model is None:
        return {}
    # Se já for um dicionário (caso venha do cache mal formatado), retorna-o
    if isinstance(model, dict):
        return model
    # Caso contrário, usa o model_dump do Pydantic
    return model.model_dump(mode="json")

def build_variant_payloads(cache):
    envolvidos = safe_dump(cache.get("envolvidos_vst")) or {}

    v1 = safe_dump(cache.get("tudo_em_um"))

    v2 = {
        "resumo_processo": (safe_dump(cache.get("mapeamento_inquerito")) or {}).get("resumo_processo"),
        "inquerito": (safe_dump(cache.get("mapeamento_inquerito")) or {}).get("inquerito"),
        "vitimas": envolvidos.get("vitimas"),
        "suspeitos": envolvidos.get("suspeitos"),
        "testemunhas": envolvidos.get("testemunhas"),
    }

    v3 = {
        "resumo_processo": safe_dump(cache.get("mapeamento")),
        "inquerito": safe_dump(cache.get("inquerito")),
        "vitimas": envolvidos.get("vitimas"),
        "suspeitos": envolvidos.get("suspeitos"),
        "testemunhas": envolvidos.get("testemunhas"),
    }

    v4 = {
        "resumo_processo": (safe_dump(cache.get("mapeamento_inquerito")) or {}).get("resumo_processo"),
        "inquerito": (safe_dump(cache.get("mapeamento_inquerito")) or {}).get("inquerito"),
        "vitimas": safe_dump(cache.get("vitimas")),
        "suspeitos": safe_dump(cache.get("suspeitos")),
        "testemunhas": safe_dump(cache.get("testemunhas")),
    }

    v5 = {
        "resumo_processo": safe_dump(cache.get("mapeamento")),
        "inquerito": safe_dump(cache.get("inquerito")),
        "vitimas": safe_dump(cache.get("vitimas")),
        "suspeitos": safe_dump(cache.get("suspeitos")),
        "testemunhas": safe_dump(cache.get("testemunhas")),
    }

    return {
        "1_node": v1,
        "2_nodes": v2,
        "3_nodes": v3,
        "4_nodes": v4,
        "5_nodes": v5,
    }