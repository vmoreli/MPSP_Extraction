from pydantic import BaseModel, Field
from typing import Optional
from langgraph.graph import StateGraph, START, END

from pipeline.schemas.extract_data_schemas import (
    Vitimas,
    Suspeitos,
    Testemunhas,
    Inquerito,
    ClassificacaoCrime,
    ResumoProcesso,
)

from pipeline.nodes.extract_data_nodes import (
    extrair_vitimas_node,
    extrair_suspeitos_node,
    extrair_testemunhas_node,
    extrair_info_inquerito_node,
    mapear_envolvidos_classificar_node,
)


# ---------------------------------------------------------
# Definição do estado do grafo
# ---------------------------------------------------------
class InqueritoTotal(BaseModel):
    """Modelo unificado para extração de informações do inquérito policial."""
    document: str
    resumo_processo: ResumoProcesso = Field(None, description="Mapeamento dos envolvidos e classificação do tipo de crime.")
    vitimas: Optional[Vitimas] = Field(None, description="Informações sobre as vítimas")
    suspeitos: Optional[Suspeitos] = Field(None, description="Informações sobre os autores")
    testemunhas: Optional[Testemunhas] = Field(None, description="Informações sobre as testemunhas")
    inquerito: Optional[Inquerito] = Field(None, description="Informações gerais do inquérito")


# Define o grafo
builder = StateGraph(InqueritoTotal)

builder.add_node("mapear envolvidos e classificar crime", mapear_envolvidos_classificar_node)
builder.add_node("extrair informações gerais do inquérito", extrair_info_inquerito_node)
builder.add_node("extrair vítimas", extrair_vitimas_node)
builder.add_node("extrair suspeitos", extrair_suspeitos_node)
builder.add_node("extrair testemunhas", extrair_testemunhas_node)

builder.set_entry_point("mapear envolvidos e classificar crime")

pipeline = builder.compile()
