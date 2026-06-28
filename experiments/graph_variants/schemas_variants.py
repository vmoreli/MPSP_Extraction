# -*- coding: utf-8 -*-
"""
Schemas combinados das variantes.

Objetivo:
- permitir parse() com validação forte
- manter a mesma lógica do pipeline base (restrições no schema)
"""
from typing import Optional, List
from pydantic import BaseModel

from extraction_pipeline.schemas.extract_data_schemas import (
    ResumoProcesso,
    Inquerito,
    Vitima,
    Pessoa,
)

# -----------------------------
# Mapeamentos
# -----------------------------

class MapeamentoOut(BaseModel):
    resumo_processo: ResumoProcesso


class InqueritoOut(BaseModel):
    inquerito: Inquerito


class MapeamentoInqueritoOut(BaseModel):
    resumo_processo: ResumoProcesso
    inquerito: Inquerito


# -----------------------------
# Envolvidos (VST)
# -----------------------------

class EnvolvidosOut(BaseModel):
    """
    Saída simplificada do prompt de envolvidos (VST).
    Contém apenas listas de pessoas, sem enriquecimento.
    """
    vitimas: Optional[List[Vitima]] = None
    suspeitos: Optional[List[Pessoa]] = None
    testemunhas: Optional[List[Pessoa]] = None


# -----------------------------
# Tudo em um
# -----------------------------

class TudoOut(BaseModel):
    resumo_processo: ResumoProcesso
    inquerito: Inquerito
    vitimas: Optional[List[Vitima]] = None
    suspeitos: Optional[List[Pessoa]] = None
    testemunhas: Optional[List[Pessoa]] = None