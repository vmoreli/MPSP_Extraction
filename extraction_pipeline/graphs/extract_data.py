from pydantic import BaseModel, Field
from typing import Optional
from langgraph.graph import StateGraph, START, END

# Importando schemas para definir estado do grafo
from extraction_pipeline.schemas.extract_data_schemas import (
  Vitimas,
  Suspeitos,
  Testemunhas,
  Inquerito
)

# Importando nós do grafo
from extraction_pipeline.nodes.extract_data_nodes import (
  extrair_vitimas_node,
  extrair_suspeitos_node,
  extrair_testemunhas_node,
  extrair_info_inquerito_node
)

# ---------------------------------------------------------
# Definição do estado do grafo
# ---------------------------------------------------------
class InqueritoTotal(BaseModel):
  """Modelo unificado para extração de informações do inquérito policial."""
  vitimas: Optional[Vitimas] = Field(None, description="Informações sobre as vítimas")
  suspeitos: Optional[Suspeitos] = Field(None, description="Informações sobre os autores")
  testemunhas: Optional[Testemunhas] = Field(None, description="Informações sobre as testemunhas")
  inquerito: Optional[Inquerito] = Field(None, description="Informações gerais do inquérito")


# Define o grafo
builder = StateGraph(InqueritoTotal)

# Adiciona os nós
builder.add_node("extrair vítimas", extrair_vitimas_node)
builder.add_node("extrair suspeitos", extrair_suspeitos_node)
builder.add_node("extrair testemunhas", extrair_testemunhas_node)
builder.add_node("extrair informações gerais do inquérito", extrair_info_inquerito_node)

# Adiciona aresta para o início
builder.add_edge(START, "extrair vítimas")

# Compila grafo
pipeline = builder.compile()