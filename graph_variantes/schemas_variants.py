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

from typing import Optional
from pydantic import BaseModel

from extraction_pipeline.schemas.extract_data_schemas import (
    ResumoProcesso,
    Inquerito,
    Vitimas,
    Suspeitos,
    Testemunhas,
)


class MapeamentoInqueritoOut(BaseModel):
    resumo_processo: ResumoProcesso
    inquerito: Inquerito


class EnvolvidosOut(BaseModel):
    vitimas: Optional[Vitimas] = None
    suspeitos: Optional[Suspeitos] = None
    testemunhas: Optional[Testemunhas] = None


class TudoOut(BaseModel):
    resumo_processo: ResumoProcesso
    inquerito: Inquerito
    vitimas: Optional[Vitimas] = None
    suspeitos: Optional[Suspeitos] = None
    testemunhas: Optional[Testemunhas] = None
