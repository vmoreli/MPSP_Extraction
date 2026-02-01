# -*- coding: utf-8 -*-
"""
Monta os 5 grafos a partir do cache de prompts.

Importante:
- NÃO chama LLM
- só reorganiza outputs já válidos
"""

from typing import Any, Dict

def build_variant_payloads(cache: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Retorna dict:
      variant_name -> payload final
    payload final sempre com:
      resumo_processo, inquerito, vitimas, suspeitos, testemunhas
    """
    # 1_node_all (tudo_em_um)
    v1 = {
        "resumo_processo": cache["tudo_em_um"].resumo_processo,
        "inquerito": cache["tudo_em_um"].inquerito,
        "vitimas": cache["tudo_em_um"].vitimas,
        "suspeitos": cache["tudo_em_um"].suspeitos,
        "testemunhas": cache["tudo_em_um"].testemunhas,
    }

    # 2_nodes_MI_VST (mapeamento_inquerito + envolvidos_vst)
    v2 = {
        "resumo_processo": cache["mapeamento_inquerito"].resumo_processo,
        "inquerito": cache["mapeamento_inquerito"].inquerito,
        "vitimas": cache["envolvidos_vst"].vitimas,
        "suspeitos": cache["envolvidos_vst"].suspeitos,
        "testemunhas": cache["envolvidos_vst"].testemunhas,
    }

    # 3_nodes_M_I_VST (mapeamento + inquerito + envolvidos_vst)
    v3 = {
        "resumo_processo": cache["mapeamento"],
        "inquerito": cache["inquerito"],
        "vitimas": cache["envolvidos_vst"].vitimas,
        "suspeitos": cache["envolvidos_vst"].suspeitos,
        "testemunhas": cache["envolvidos_vst"].testemunhas,
    }

    # 4_nodes_M_I_V_S_T (mapeamento + inquerito + vitimas + suspeitos + testemunhas)
    v4 = {
        "resumo_processo": cache["mapeamento"],
        "inquerito": cache["inquerito"],
        "vitimas": cache["vitimas"],
        "suspeitos": cache["suspeitos"],
        "testemunhas": cache["testemunhas"],
    }

    # 5_nodes (baseline – mesmo payload final; diferença é conceitual no paper)
    v5 = {
        "resumo_processo": cache["mapeamento"],
        "inquerito": cache["inquerito"],
        "vitimas": cache["vitimas"],
        "suspeitos": cache["suspeitos"],
        "testemunhas": cache["testemunhas"],
    }

    return {
        "1_node_all": v1,
        "2_nodes_MI_VST": v2,
        "3_nodes_M_I_VST": v3,
        "4_nodes_M_I_V_S_T": v4,
        "5_nodes": v5,
    }
