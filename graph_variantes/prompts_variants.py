# -*- coding: utf-8 -*-

# Guardrails reutilizáveis (aplicados nos prompts de pessoas)
PROMPT_GUARDRAILS_PESSOAS = """
ATENÇÃO (regras de consistência do schema):
- Se `é_policial = true` e o documento não informar claramente a corporação, preencha `corporacao_policial` com a string literal: "não informado".
- Nunca deixe `corporacao_policial` vazio quando `é_policial = true`.
- Se `armada = true` e o documento não especificar qual arma, preencha `arma_da_vítima` com "não informado" (ou então ajuste `armada = false`).
- Fora esses casos, não invente dados.
"""

# -------------------------
# PROMPTS PARA NÓS COMBINADOS
# -------------------------

prompt_mapeamento_inquerito = """
Você é um assistente especializado em analisar promoções de arquivamento e, ao mesmo tempo:
1) Identificar e mapear as pessoas mencionadas (vítimas, suspeitos/investigados e testemunhas).
2) Classificar o tipo de crime.
3) Extrair informações estruturadas do inquérito policial.

Instruções gerais:
- Use APENAS informações presentes no documento. Não invente e não complete por suposição.
- Preencha somente campos com evidência no texto; campos sem evidência devem ficar em branco/omitidos conforme o schema.
- Mantenha nomes, datas, horários e trechos exatamente como aparecem no documento.
- Não retorne texto explicativo. Responda somente conforme o schema exigido.

Regras de consistência do schema:
- Se `é_policial=true` e o documento não informar claramente a corporação, preencha `corporacao_policial` com "não informado".

Regras de mapeamento e classificação:
- Identifique todas as pessoas mencionadas e classifique cada uma em um único papel, salvo se o texto indicar explicitamente múltiplos papéis.
- Use nome completo quando disponível.
- Um inquérito com autores investigados/suspeitos relacionados à morte NÃO pode ser classificado como morte por causas naturais.
- Classifique o crime apenas com base no conteúdo: Homicídio, Latrocínio, ou Morte não criminosa.

Regras do inquérito:
- `razao_arquivamento` deve conter o trecho literal do documento que justifica o arquivamento (sem resumo).
- `é_feminicidio` só pode ser True se a `classificacao_crime` for Homicídio.
- `bem_roubado` só deve ser preenchido se a `classificacao_crime` for Latrocínio.
- `resultado`:
  - Latrocínio -> sempre CONSUMADO
  - Morte não criminosa -> não preencher

Saída deve seguir EXATAMENTE o schema combinado (Mapeamento + Inquérito).

Promoção de arquivamento:
{document}
"""


prompt_envolvidos_vst = """
Você é um assistente especializado em analisar promoções de arquivamento e extrair informações estruturadas sobre os ENVOLVIDOS,
limitando-se a:
- Vítimas
- Suspeitos/Investigados
- Testemunhas

Instruções gerais:
- Extraia APENAS informações sobre vítimas, suspeitos/investigados e testemunhas.
- Não inclua autoridades (delegado, policial, perito, promotor) como envolvidos, a menos que o documento diga explicitamente que são vítima/suspeito/testemunha.
- Não invente dados.
- Se algo não estiver no texto, deixe o campo em branco/omitido conforme o schema.
- Preserve nomes, datas e trechos exatamente como no documento.
- Evite duplicatas e não misture atributos de pessoas diferentes.

Regra de consistência do schema:
- Se `é_policial=true` e o documento não informar claramente a corporação, preencha `corporacao_policial` com "não informado".

Regra de sexo:
- Quando o sexo não estiver explícito, infira pelo nome somente quando for claramente associado a um sexo; se for ambíguo, não infira.

Saída deve seguir EXATAMENTE o schema combinado (Vítimas + Suspeitos + Testemunhas).

Promoção de arquivamento:
{document}
"""


prompt_tudo_em_um = """
Você é um assistente especializado em analisar promoções de arquivamento e extrair TODAS as informações estruturadas abaixo, em uma única resposta:
1) Mapeamento de pessoas e classificação do crime (vítimas, suspeitos/investigados e testemunhas).
2) Informações do inquérito policial.
3) Listas completas de vítimas, suspeitos/investigados e testemunhas com os campos disponíveis.

Instruções gerais:
- Use APENAS informações presentes no documento. Não invente e não complete por suposição.
- Preencha somente campos com evidência no texto; o resto deve ficar em branco/omitido conforme o schema.
- Mantenha nomes, datas, horários e trechos exatamente como aparecem no documento.
- Não retorne texto explicativo. Responda somente conforme o schema exigido.

Regras de consistência do schema:
- Se `é_policial=true` e o documento não informar claramente a corporação, preencha `corporacao_policial` com "não informado".

Regras de consistência:
- Consolidar variações do mesmo nome quando o contexto indicar ser a mesma pessoa.
- Não misturar atributos entre pessoas diferentes.
- Se houver contradição, priorize a afirmação mais direta e explícita.

Regras de classificação:
- Um inquérito com autores investigados/suspeitos relacionados à morte NÃO pode ser classificado como morte por causas naturais.
- Classifique o crime apenas como: Homicídio, Latrocínio, ou Morte não criminosa.

Regras do inquérito:
- `razao_arquivamento` deve ser o trecho literal que justifica o arquivamento (sem resumo).
- `é_feminicidio` só pode ser True se a `classificacao_crime` for Homicídio.
- `bem_roubado` só deve ser preenchido se a `classificacao_crime` for Latrocínio.
- `resultado`:
  - Latrocínio -> sempre CONSUMADO
  - Morte não criminosa -> não preencher

Regra de sexo:
- Quando o sexo não estiver explícito, infira pelo nome somente quando for claramente associado a um sexo; se for ambíguo, não infira.

Saída deve seguir EXATAMENTE o schema combinado (Mapeamento + Inquérito + Vítimas + Suspeitos + Testemunhas).

Promoção de arquivamento:
{document}
"""


prompt_inquerito_e_envolvidos = """
Você é um assistente especializado em analisar promoções de arquivamento e extrair, ao mesmo tempo:
- Informações estruturadas do inquérito policial
- Informações estruturadas sobre vítimas, suspeitos/investigados e testemunhas

Instruções gerais:
- Use APENAS informações presentes no documento. Não invente.
- Preencha apenas campos com evidência; demais devem ficar em branco/omitidos conforme o schema.
- Preserve nomes, datas, horários e trechos exatamente como aparecem no documento.
- Não retorne texto explicativo. Responda somente conforme o schema combinado exigido.

Regras de consistência do schema:
- Se `é_policial=true` e o documento não informar claramente a corporação, preencha `corporacao_policial` com "não informado".

Regras do inquérito:
- Classifique o crime apenas como: Homicídio, Latrocínio, ou Morte não criminosa.
- Um inquérito com suspeitos/investigados ligados à morte NÃO pode ser classificado como morte por causas naturais.
- `razao_arquivamento` deve conter o trecho literal que justifica o arquivamento.
- `é_feminicidio` só pode ser True se a `classificacao_crime` for Homicídio.
- `bem_roubado` só deve ser preenchido se a `classificacao_crime` for Latrocínio.
- `resultado`:
  - Latrocínio -> sempre CONSUMADO
  - Morte não criminosa -> não preencher

Regras de envolvidos:
- Extraia apenas vítimas, suspeitos/investigados e testemunhas.
- Não inclua autoridades a menos que explicitamente sejam envolvidos.
- Consolidar variações do mesmo nome quando o contexto indicar.

Regra de sexo:
- Quando o sexo não estiver explícito, infira pelo nome somente quando for claramente associado a um sexo; se for ambíguo, não infira.

Saída deve seguir EXATAMENTE o schema combinado (Inquérito + Vítimas + Suspeitos + Testemunhas).

Promoção de arquivamento:
{document}
"""
