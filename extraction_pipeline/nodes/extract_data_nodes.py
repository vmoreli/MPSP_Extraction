import json
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
    Inquerito
)


# ---------------------------------------------------------
# Nó para extrair informações das vítimas
# ---------------------------------------------------------
def extrair_vitimas_node(state) -> Command[Literal["extrair suspeitos"]]:
    document = state.get("document")
    prompt = prompt_vitimas.format(document=document)

    response_content = call_llm(prompt=prompt, output_schema=Vitimas)
    vitimas = Vitimas.model_validate_json(response_content)

    goto = "extrair suspeitos"

    return Command(
        goto=goto,
        update={"vitimas": vitimas}
    )


# ---------------------------------------------------------
# Nó para extrair informações dos suspeitos
# ---------------------------------------------------------
def extrair_suspeitos_node(state) -> Command[Literal["extrair testemunhas"]]:
    document = state.get("document")
    prompt = prompt_suspeitos.format(document=document)

    response_content = call_llm(prompt=prompt, output_schema=Suspeitos)
    suspeitos = Suspeitos.model_validate_json(response_content)

    goto = "extrair testemunhas"

    return Command(
        goto=goto,
        update={"suspeitos": suspeitos}
    )


# ---------------------------------------------------------
# Nó para extrair informações das testemunhas
# ---------------------------------------------------------
def extrair_testemunhas_node(state) -> Command[Literal["extrair informações gerais do inquérito"]]:
    document = state.get("document")
    prompt = prompt_testemunhas.format(document=document)

    response_content = call_llm(prompt=prompt, output_schema=Testemunhas)
    testemunhas = Testemunhas.model_validate_json(response_content)

    goto = "extrair informações gerais do inquérito"

    return Command(
        goto=goto,
        update={"testemunhas": testemunhas}
    )


# ---------------------------------------------------------
# Nó para extrair informações gerais do processo
# ---------------------------------------------------------
def extrair_info_inquerito_node(state) -> Command[END]:
    document = state.get("document")
    prompt = prompt_inquerito_info.format(document=document)

    response_content = call_llm(prompt=prompt, output_schema=Inquerito)
    inquerito_info = Inquerito.model_validate_json(response_content)

    goto = "END"

    return Command(
        goto=goto,
        update={"inquerito": inquerito_info}
    )


