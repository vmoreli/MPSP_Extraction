from langgraph.types import Command
from typing import Literal
from langgraph.graph import END
from extraction_pipeline.services.llm_services import call_llm

from extraction_pipeline.prompts.prompts import (
    prompt_vitimas,
    prompt_suspeitos,
    prompt_testemunhas,
    prompt_inquerito_info,
    prompt_mapeamento
)

from extraction_pipeline.schemas.extract_data_schemas import (
    Vitimas,
    Suspeitos,
    Testemunhas,
    Inquerito,
    ResumoProcesso,
    ClassificacaoCrime
)

# ---------------------------------------------------------
# Nó para mapear envolvidos e classificar processo
# ---------------------------------------------------------
def mapear_envolvidos_classificar_node(state) -> Command[Literal["extrair informações gerais do inquérito", END]]:
    document = state.document
    prompt = prompt_mapeamento.format(document=document)

    response_content = call_llm(prompt=prompt, output_schema=ResumoProcesso)
    resumo_processo = ResumoProcesso.model_validate_json(response_content)

    eh_morte_natural = (resumo_processo.classificacao_crime == ClassificacaoCrime.MORTE_CAUSAS_NATURAIS)

    goto = END if eh_morte_natural else "extrair informações gerais do inquérito" 

    return Command(
        goto=goto,
        update={"resumo_processo": resumo_processo}
    )


# ---------------------------------------------------------
# Nó para extrair informações gerais do processo
# ---------------------------------------------------------
def extrair_info_inquerito_node(state) -> Command[Literal["extrair vítimas", "extrair suspeitos", "extrair testemunhas", END]]:
    document = state.document
    resumo_processo = state.resumo_processo
    prompt = prompt_inquerito_info.format(document=document, classification=resumo_processo.classificacao_crime)

    response_content = call_llm(prompt=prompt, output_schema=Inquerito)
    inquerito_info = Inquerito.model_validate_json(response_content)

    pessoas_envolvidas = resumo_processo.pessoas_envolvidas
    vitimas = pessoas_envolvidas.vitimas
    suspeitos = pessoas_envolvidas.suspeitos_investigados
    testemunhas = pessoas_envolvidas.testemunhas

    goto = END
    if vitimas:
        goto = "extrair vitimas"
        print(f"-> Próximo passo: {goto}")
    if suspeitos:
        goto = "extrair suspeitos"
        print(f"-> Próximo passo: {goto}")
    elif testemunhas:
        goto = "extrair testemunhas"
        print(f"-> Próximo passo: {goto}")
    else:
        print("-> Próximo passo: Ninguém mais para extrair. Finalizando.")

    return Command(
        goto=goto,
        update={"inquerito": inquerito_info}
    )

# ---------------------------------------------------------
# Nó para extrair informações das vítimas
# ---------------------------------------------------------
def extrair_vitimas_node(state) -> Command[Literal["extrair suspeitos", "extrair testemunhas", END]]:
    document = state.document
    resumo_processo = state.resumo_processo
    vitimas_lista = resumo_processo.pessoas_envolvidas.vitimas

    vitimas_str = ", ".join(vitimas_lista)

    prompt = prompt_vitimas.format(document=document, vitimas=vitimas_str)

    response_content = call_llm(prompt=prompt, output_schema=Vitimas)
    vitimas = Vitimas.model_validate_json(response_content)

    # Decisão do próximo passo
    goto = END # O padrão é terminar se não houver mais ninguém
    resumo_processo = state.resumo_processo
    pessoas_envolvidas = resumo_processo.pessoas_envolvidas
    suspeitos = pessoas_envolvidas.suspeitos_investigados
    testemunhas = pessoas_envolvidas.testemunhas

    if suspeitos:
        goto = "extrair suspeitos"
        print(f"-> Próximo passo: {goto}")
    elif testemunhas:
        goto = "extrair testemunhas"
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
def extrair_suspeitos_node(state) -> Command[Literal["extrair testemunhas", END]]:
    document = state.document
    resumo_processo = state.resumo_processo
    suspeitos_lista = resumo_processo.pessoas_envolvidas.suspeitos_investigados

    suspeitos_str = ", ".join(suspeitos_lista)

    prompt = prompt_suspeitos.format(document=document, suspeitos=suspeitos_str)

    response_content = call_llm(prompt=prompt, output_schema=Suspeitos)
    suspeitos = Suspeitos.model_validate_json(response_content)

    # Decisão do próximo passo
    goto = END # O padrão é terminar se não houver mais ninguém
    pessoas_envolvidas = resumo_processo.pessoas_envolvidas
    testemunhas = pessoas_envolvidas.testemunhas

    if testemunhas:
        goto = "extrair testemunhas"
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
    resumo_processo = state.resumo_processo
    testemunhas_lista = resumo_processo.pessoas_envolvidas.testemunhas

    testemunhas_str = ", ".join(testemunhas_lista)

    prompt = prompt_testemunhas.format(document=document, testemunhas=testemunhas_str)

    response_content = call_llm(prompt=prompt, output_schema=Testemunhas)
    testemunhas = Testemunhas.model_validate_json(response_content)

    goto = END

    return Command(
        goto=goto,
        update={"testemunhas": testemunhas}
    )





