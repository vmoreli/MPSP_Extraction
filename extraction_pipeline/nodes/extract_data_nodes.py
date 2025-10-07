from langgraph.types import Command
from typing import Literal
from langgraph.graph import END
from extraction_pipeline.services.llm_services import call_llm

from extraction_pipeline.prompts.prompts import (
    prompt_vitimas,
    prompt_suspeitos,
    prompt_testemunhas,
    prompt_inquerito_info
)

from extraction_pipeline.schemas.extract_data_schemas import (
    Vitimas,
    Suspeitos,
    Testemunhas,
    Inquerito,
    ClassificacaoCrime
)
    

# ---------------------------------------------------------
# Nó para extrair informações gerais do processo
# ---------------------------------------------------------
def extrair_info_inquerito_node(state) -> Command[Literal["extrair vítimas"]]:
    document = state.document
    prompt = prompt_inquerito_info.format(document=document)

    response_content = call_llm(prompt=prompt, output_schema=Inquerito)
    inquerito_info = Inquerito.model_validate_json(response_content)

    return Command(
        update={"inquerito": inquerito_info}
    )

# ---------------------------------------------------------
# Nó para extrair informações das vítimas
# ---------------------------------------------------------
def extrair_vitimas_node(state) -> Command[Literal["extrair suspeitos"]]:
    document = state.document
    vitimas_lista = state.inquerito.pessoas_envolvidas.vitimas

    vitimas_str = ", ".join(vitimas_lista)

    prompt = prompt_vitimas.format(document=document, vitimas=vitimas_str)

    response_content = call_llm(prompt=prompt, output_schema=Vitimas)
    vitimas = Vitimas.model_validate_json(response_content)

    # Decisão do próximo passo
    goto = END # O padrão é terminar se não houver mais ninguém
    inquerito_info = state.inquerito
    suspeitos = inquerito_info.pessoas_envolvidas.suspeitos_investigados
    testemunhas = inquerito_info.pessoas_envolvidas.testemunhas

    if suspeitos:
        goto = "extrair_suspeitos"
        print(f"-> Próximo passo: {goto}")
    elif testemunhas:
        goto = "extrair_testemunhas"
        print(f"-> Próximo passo: {goto}")
    else:
        print("-> Próximo passo: Ninguém mais para extrair. Finalizando.")

    return Command(
        goto=goto,
        update={"vitimas": vitimas}
    )


# ---------------------------------------------------------
# Nó para extrair informações dos suspeitos
# ---------------------------------------------------------
def extrair_suspeitos_node(state) -> Command[Literal["extrair testemunhas"]]:
    document = state.document
    suspeitos_lista = state.inquerito.pessoas_envolvidas.suspeitos_investigados

    suspeitos_str = ", ".join(suspeitos_lista)

    prompt = prompt_suspeitos.format(document=document, suspeitos=suspeitos_str)

    response_content = call_llm(prompt=prompt, output_schema=Suspeitos)
    suspeitos = Suspeitos.model_validate_json(response_content)

    # Decisão do próximo passo
    goto = END # O padrão é terminar se não houver mais ninguém
    inquerito_info = state.inquerito
    testemunhas = inquerito_info.pessoas_envolvidas.testemunhas

    if testemunhas:
        goto = "extrair_testemunhas"
        print(f"-> Próximo passo: {goto}")
    else:
        print("-> Próximo passo: Ninguém mais para extrair. Finalizando.")

    return Command(
        goto=goto,
        update={"suspeitos": suspeitos}
    )


# ---------------------------------------------------------
# Nó para extrair informações das testemunhas
# ---------------------------------------------------------
def extrair_testemunhas_node(state):
    document = state.document
    testemunhas_lista = state.inquerito.pessoas_envolvidas.testemunhas

    testemunhas_str = ", ".join(testemunhas_lista)

    prompt = prompt_testemunhas.format(document=document, testemunhas=testemunhas_str)

    response_content = call_llm(prompt=prompt, output_schema=Testemunhas)
    testemunhas = Testemunhas.model_validate_json(response_content)

    goto = END

    return Command(
        goto=goto,
        update={"testemunhas": testemunhas}
    )





