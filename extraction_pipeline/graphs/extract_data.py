from pydantic import BaseModel, Field
from typing import Optional
from langgraph.graph import StateGraph, START, END

# Importando schemas para definir estado do grafo
from extraction_pipeline.schemas.extract_data_schemas import (
  Vitimas,
  Suspeitos,
  Testemunhas,
  Inquerito,
  ClassificacaoCrime
)

# Importando nós do grafo
from extraction_pipeline.nodes.extract_data_nodes import (
  extrair_vitimas_node,
  extrair_suspeitos_node,
  extrair_testemunhas_node,
  extrair_info_inquerito_node
)

# Função para roteamento a partir da extração da info básica
def decidir_proximo_passo_extracao(inquerito_info: dict) -> str:
    """
    Analisa o estado para decidir o próximo passo no fluxo de extração.
    A ordem de prioridade é: Vítimas -> Suspeitos -> Testemunhas.
    Se o crime não tiver indício de crime, o fluxo é encerrado.
    """
    print("--- ROTEADOR: Decidindo próximo passo da extração ---")
    
    # Primeira verificação: Interromper se for morte sem indício de crime
    if inquerito_info.inquerito.classificacao_crime == ClassificacaoCrime.MORTE_SEM_INDICIO_DE_CRIME:
        print("-> Rota: Morte sem indício de crime. Finalizando o fluxo.")
        return END

    # Acessar as listas de pessoas
    vitimas = inquerito_info.pessoas_envolvidas.vitimas
    suspeitos = inquerito_info.pessoas_envolvidas.suspeitos_investigados
    testemunhas = inquerito_info.pessoas_envolvidas.testemunhas
    
    # Lógica de roteamento com prioridade
    if vitimas:
        print("-> Rota: Vítimas identificadas. Indo para 'extrair_vitimas'.")
        return "extrair_vitimas"
    elif suspeitos:
        print("-> Rota: Sem vítimas, mas com suspeitos. Indo para 'extrair_suspeitos'.")
        return "extrair_suspeitos"
    elif testemunhas:
        print("-> Rota: Sem vítimas ou suspeitos, mas com testemunhas. Indo para 'extrair_testemunhas'.")
        return "extrair_testemunhas"
    else:
        # Caso não haja ninguém para extrair, o fluxo pode terminar
        print("-> Rota: Nenhuma pessoa relevante identificada para extração. Finalizando o fluxo.")
        return END

# ---------------------------------------------------------
# Definição do estado do grafo
# ---------------------------------------------------------
class InqueritoTotal(BaseModel):
  """Modelo unificado para extração de informações do inquérito policial."""
  document: str
  vitimas: Optional[Vitimas] = Field(None, description="Informações sobre as vítimas")
  suspeitos: Optional[Suspeitos] = Field(None, description="Informações sobre os autores")
  testemunhas: Optional[Testemunhas] = Field(None, description="Informações sobre as testemunhas")
  inquerito: Optional[Inquerito] = Field(None, description="Informações gerais do inquérito")


# Define o grafo
builder = StateGraph(InqueritoTotal)

# Adiciona os nós
builder.add_node("extrair informações gerais do inquérito", extrair_info_inquerito_node)
builder.add_node("extrair vítimas", extrair_vitimas_node)
builder.add_node("extrair suspeitos", extrair_suspeitos_node)
builder.add_node("extrair testemunhas", extrair_testemunhas_node)

# Adiciona aresta para o início
builder.set_entry_point("extrair informações gerais do inquérito")

# 4. Adicionar a aresta condicional
builder.add_conditional_edges(
    # O nó de origem da decisão
    "extrair informações gerais do inquérito",
    # A função que toma a decisão
    decidir_proximo_passo_extracao,
    # O mapeamento: o que a função retorna -> para qual nó ir
    {
        "extrair_vitimas": "extrair vítimas",
        "extrair_suspeitos": "extrair suspeitos",
        "extrair_testemunhas": "extrair testemunhas",
        END: END
    }
)

# Compila grafo
pipeline = builder.compile()