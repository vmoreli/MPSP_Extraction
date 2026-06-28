
# -*- coding: utf-8 -*-
"""
Schemas combinados das variantes.

Objetivo:
- permitir parse() com validação forte
- manter a mesma lógica do pipeline base (restrições no schema)

Obs:
- As regras condicionais continuam no schema original (ex: Vitimas).
- Aqui só juntamos outputs em modelos combinados.
"""

from typing import Any, Dict
from pydantic import BaseModel


def safe_dump(val):
    if isinstance(val, BaseModel):
        return val.model_dump()
    return None


def build_variant_payloads(cache: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:

    envolvidos = cache.get("envolvidos_vst")

    v1 = safe_dump(cache.get("tudo_em_um"))

    v2 = {
        "resumo_processo": safe_dump(cache.get("mapeamento_inquerito")) and
                           safe_dump(cache.get("mapeamento_inquerito")).get("resumo_processo"),
        "inquerito": safe_dump(cache.get("mapeamento_inquerito")) and
                     safe_dump(cache.get("mapeamento_inquerito")).get("inquerito"),
        "vitimas": safe_dump(envolvidos.vitimas) if envolvidos else None,
        "suspeitos": safe_dump(envolvidos.suspeitos) if envolvidos else None,
        "testemunhas": safe_dump(envolvidos.testemunhas) if envolvidos else None,
    }

    v3 = {
        "resumo_processo": safe_dump(cache.get("mapeamento")),
        "inquerito": safe_dump(cache.get("inquerito")),
        "vitimas": safe_dump(envolvidos.vitimas) if envolvidos else None,
        "suspeitos": safe_dump(envolvidos.suspeitos) if envolvidos else None,
        "testemunhas": safe_dump(envolvidos.testemunhas) if envolvidos else None,
    }

    v4 = {
        "resumo_processo": safe_dump(cache.get("mapeamento_inquerito")) and
                           safe_dump(cache.get("mapeamento_inquerito")).get("resumo_processo"),
        "inquerito": safe_dump(cache.get("mapeamento_inquerito")) and
                     safe_dump(cache.get("mapeamento_inquerito")).get("inquerito"),
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