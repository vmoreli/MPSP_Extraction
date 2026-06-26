"""
Prompts combinados para as variantes do experimento.
Importa os prompts base de prompts.base para evitar duplicação.
"""

from prompts.base import (
    prompt_vitimas,
    prompt_suspeitos,
    prompt_testemunhas,
    prompt_mapeamento,
    prompt_inquerito_info,
    prompt_compare_str,
)

__all__ = [
    "prompt_vitimas",
    "prompt_suspeitos",
    "prompt_testemunhas",
    "prompt_mapeamento",
    "prompt_inquerito_info",
    "prompt_compare_str",
    "prompt_envolvidos_vst",
    "prompt_mapeamento_inquerito",
    "prompt_inquerito_e_envolvidos",
    "prompt_tudo_em_um",
]

prompt_envolvidos_vst = """
Você é um assistente especializado em analisar promoções de arquivamento e extrair, de forma conjunta, informações estruturadas sobre: Vítimas, Suspeitos/Investigados e Testemunhas.

Instruções Gerais:
- Extraia **apenas informações explícitas** no documento.
- Caso alguma informação não esteja disponível, não preencha o respectivo campo. Não invente dados e não preencha com "não informado".
- Quando o sexo não for explicitamente informado, **infira pelo nome**.
- Cada pessoa deve aparecer apenas no bloco correspondente ao seu papel. Não duplique registros.

Regras de Negócio para Pessoas:
- **é_policial**: Só marque como `True` se a corporação estiver explicitamente descrita. Se `True`, preencha obrigatoriamente `corporacao_policial`. Se `False`, deixe a corporação em branco.
- **armada (Vítimas)**: Só marque como `True` se a arma estiver explicitamente descrita no texto. Se `True`, preencha obrigatoriamente `arma_da_vítima`.

Promoção de arquivamento:
{document}
"""

prompt_mapeamento_inquerito = """
Você é um assistente especializado em analisar promoções de arquivamento e realizar três tarefas conjuntamente:
1) Mapeamento e classificação de todas as pessoas mencionadas.
2) Classificação do tipo de crime.
3) Extração estruturada das informações do inquérito policial.

Instruções Gerais:
- Extraia **apenas informações explícitas** no documento. Não invente dados.
- Campos sem informação devem permanecer em branco. O que for "não informado" não precisa ser preenchido.
- Preserve datas, horários e trechos literais exatamente como aparecem.

Regras para Mapeamento:
- Identifique todas as pessoas usando nomes completos sempre que disponíveis.
- Classifique o crime como Homicídio, Latrocínio, ou Morte por causas naturais.
- **Importante**: Um inquérito com suspeitos ligados à morte não pode ser "Morte por causas naturais".

Regras para Inquérito:
- O campo `razao_arquivamento` deve conter o **trecho literal** que justifica o arquivamento.
- O campo `é_feminicidio` só pode ser `True` se for **Homicídio**.
- O campo `bem_roubado` deve ser preenchido apenas se for **Latrocínio**.
- O campo `resultado`:
    - Homicídio → "Consumado" ou "Tentado" apenas se explícito; senão, deixe em branco.
    - Latrocínio → Sempre "Consumado".
    - Morte por causas naturais → Deixe em branco.

Promoção de arquivamento:
{document}
"""

prompt_inquerito_e_envolvidos = """
Você é um assistente especializado em analisar promoções de arquivamento e extrair, de forma conjunta:
- Informações estruturadas do Inquérito
- Informações detalhadas sobre Vítimas, Suspeitos/Investigados e Testemunhas

Instruções Gerais:
- Extraia **apenas informações explícitas** no documento. Não invente dados.
- Campos sem informação devem permanecer em branco.
- Preserve datas, horários e trechos literais exatamente como aparecem.

Regras para Pessoas (Vítimas, Suspeitos, Testemunhas):
- **Sexo**: Quando não explícito, infira pelo nome.
- **é_policial**: Só marque como `True` se a corporação estiver explicitamente descrita.
- **armada (Vítimas)**: Só marque como `True` se a arma estiver explicitamente descrita.

Regras para Inquérito:
- Classifique o crime (Homicídio, Latrocínio ou Morte por causas naturais).
- `razao_arquivamento`: Deve ser o trecho literal do documento.
- `é_feminicidio`: Apenas se for **Homicídio**.
- `bem_roubado`: Apenas se for **Latrocínio**.
- `resultado`: Conforme o tipo de crime.

Promoção de arquivamento:
{document}
"""

prompt_tudo_em_um = """
Você é um assistente especializado em analisar promoções de arquivamento e extrair, em uma única etapa, todas as informações estruturadas sobre:
1) Mapeamento (Resumo do Processo e Classificação do Crime)
2) Dados do Inquérito Policial
3) Dados detalhados de Vítimas, Suspeitos/Investigados e Testemunhas

Instruções Gerais:
- Extraia **apenas informações explícitas** no documento. Não invente dados.
- Campos sem informação devem permanecer em branco.
- Preserve trechos literais exatamente como aparecem.

Regras para Mapeamento e Inquérito:
- Classifique como Homicídio, Latrocínio ou Morte por causas naturais.
- `é_feminicidio`: Apenas se for **Homicídio**.
- `bem_roubado`: Apenas se for **Latrocínio**.
- `resultado`: Conforme tipo de crime.

Regras para Pessoas (Envolvidos):
- **Sexo**: Quando não explícito, infira pelo nome.
- **é_policial**: Só marque `True` se a corporação estiver explícita.
- **armada (Vítimas)**: Só marque `True` se o texto mencionar a arma.

Promoção de arquivamento:
{document}
"""
