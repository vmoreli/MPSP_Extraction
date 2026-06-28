# -*- coding: utf-8 -*-

"""
Prompts variants oficiais do experimento.
"""

prompt_vitimas = """
Você é um assistente especializado em analisar promoções de arquivamento e extrair informações estruturadas sobre as vítimas.  
Siga cuidadosamente as instruções abaixo:  

Instruções:
- Extraia **apenas informações sobre as vítimas** mencionadas no documento.  
- Quando o sexo da vítima não for explicitamente informado, **infira pelo nome**.  
- Caso alguma informação não esteja disponível, não preencha o respectivo campo. Não invente dados e não preencha com "não informado".  
- Sua resposta deve seguir **exatamente** o schema completo definido para vítimas. 
- O que for "não informado" não precisa ser preenchido.

Vítimas:
{vitimas}

Promoção de arquivamento:
{document}
"""


prompt_suspeitos = """
Você é um assistente especializado em analisar promoções de arquivamento e extrair informações estruturadas sobre os autores suspeitos/investigados.  
Siga cuidadosamente as instruções abaixo:

Instruções:
- Extraia **apenas informações sobre os autores suspeitos/investigados** mencionadas no documento.
- Quando o sexo do indivíduo não for fornecido explicitamente, infira o sexo da pessoa pelo nome.
- Caso alguma informação não esteja disponível, não preencha o respectivo campo. Não invente dados e não preencha com "não informado".
- Sua resposta deve seguir **exatamente** o schema completo definido para suspeitos.
- O que for "não informado" não precisa ser preenchido.

Suspeitos:
{suspeitos}

Promoção de arquivamento:
{document}    
"""

prompt_testemunhas = """
Você é um assistente especializado em analisar promoções de arquivamento e extrair informações estruturadas sobre as testemunhas.  
Siga cuidadosamente as instruções abaixo:

Instruções:
- Extraia **apenas informações sobre as testemunhas** mencionadas no documento.
- Quando o sexo do indivíduo não for fornecido explicitamente, infira o sexo da pessoa pelo nome.
- Caso alguma informação não esteja disponível, não preencha o respectivo campo. Não invente dados e não preencha com "não informado".
- O que for "não informado" não precisa ser preenchido.

Testemunhas:
{testemunhas}

Promoção de arquivamento:
{document}    
"""

prompt_mapeamento = """
Você é um assistente especializado em analisar promoções de arquivamento e:
1) Identificar as pessoas mencionadas e classificá-las de acordo com o papel desempenhado no inquérito.
2) Classificar o tipo de crime: homicídio, latrocínio ou mortes por causas naturais.

Instruções:
- Identifique **todas as pessoas mencionadas** no texto, incluindo vítimas, autores (inclui também suspeitos/investigados) e testemunhas.
- Use nomes **completos** sempre que disponíveis.
- Classifique cada pessoa em **apenas um papel**, a menos que o texto indique explicitamente que ela exerceu mais de um.
- Um inquérito que tenha autores investigados por uma morte não pode ser tratado como morte por causas naturais.

Promoção de arquivamento:
{document}
"""

prompt_inquerito_info = """
Você é um assistente especializado em analisar promoções de arquivamento e extrair informações estruturadas sobre o inquérito policial.

Sua tarefa é **extrair apenas os detalhes do inquérito**, conforme o schema de saída.

Instruções Gerais:
- Caso alguma informação não esteja disponível, deixe o campo em branco — nunca invente ou use "não informado".
- Mantenha datas, horários e trechos de texto exatamente como aparecem no documento.

Instruções específicas:
- Classifique o crime conforme o conteúdo do texto (Homicídio, Latrocínio, ou Morte não criminosa).
- Considere como **morte por causas naturais** apenas aquelas que não decorrem da ação de suspeitos/investigados.
- O campo `razao_arquivamento` deve conter o **trecho literal** que justifica o arquivamento, sem resumo ou interpretação.
- As seguintes regras de negócio **devem ser respeitadas**:
    - O campo `é_feminicidio` só pode ser `True` se a `classificacao_crime` for **Homicídio**.
    - O campo `bem_roubado` deve ser preenchido apenas se a `classificacao_crime` for **Latrocínio**.
    - O campo `resultado` segue a lógica:
        - **Latrocínio** → sempre `CONSUMADO`
        - **Morte não criminosa** → campo não preenchido

Tipo de crime:
{classification}

Promoção de arquivamento:
{document}
"""

prompt_compare_str = """
Você deve comparar duas strings que se referem ao mesmo campo.

String de referência (ground truth):
{gt_str}

String avaliada (valor extraído ou previsto):
{value_str}

Instruções:
- Determine se a string avaliada representa corretamente a string de referência.
- Considere sinônimos, diferenças de formatação ou pequenas variações que não alterem o significado.
"""

prompt_envolvidos_vst = """
Você é um assistente especializado em analisar promoções de arquivamento e extrair informações estruturadas sobre:

- Vítimas
- Suspeitos/Investigados
- Testemunhas

Siga cuidadosamente as instruções abaixo.

Instruções Gerais:
- Utilize apenas informações explicitamente presentes no documento.
- Não invente dados e não utilize "não informado".
- Campos sem informação disponível devem permanecer em branco.
- Quando o sexo não estiver explícito, infira pelo nome.
- Cada pessoa deve aparecer apenas no bloco correspondente ao seu papel.
- Não duplique registros.
- A resposta deve seguir exatamente o schema combinado (Vítimas + Suspeitos + Testemunhas).
- Não inclua comentários ou explicações adicionais.

Regras de Classificação:
- Inclua apenas pessoas claramente identificadas como vítimas, suspeitos/investigados ou testemunhas.
- Não inclua pessoas mencionadas sem indicação clara de papel.
- Não preencha campos que não tenham evidência textual.

Regras Campos
- Nunca marque é_policial como true se o texto não afirmar explicitamente que a pessoa é policial.
- Se é_policial for true, corporacao_policial deve estar explícita, do contrário deve ser false
- Nunca marque armada como true se o texto não mencionar arma.

A resposta deve seguir EXATAMENTe o schema combinado.

Promoção de arquivamento:
{document}
"""

prompt_mapeamento_inquerito = """
Você é um assistente especializado em analisar promoções de arquivamento, extrair informações estruturadas sobre o inquérito policial.

1) Identificação e classificação de todas as pessoas mencionadas.
2) Classificação do tipo de crime.
3) Extração estruturada das informações do inquérito.

Instruções Gerais:
- Utilize apenas informações explicitamente presentes no documento.
- Não invente dados e não utilize "não informado".
- Campos sem informação devem permanecer em branco.
- Preserve datas e trechos literais exatamente como aparecem.
- Não inclua explicações.

Identificação de Pessoas:
- Identifique todas as pessoas mencionadas como vítima, suspeito/investigado ou testemunha.
- Use nomes completos sempre que disponíveis.
- Classifique cada pessoa em apenas um papel, salvo indicação expressa de múltiplos papéis.

Classificação do Crime:
- Classifique como:
    - Homicídio
    - Latrocínio
    - Morte por causas naturais
- Não classifique como "Morte por causas naturais" se houver suspeitos ligados à morte.

Regras do inquérito:
- **razao_arquivamento** deve conter o trecho literal.
- **é_feminicidio** apenas se for Homicídio.
- **bem_roubado** apenas se for Latrocínio.
- **resultado**:
    - Homicídio → "Consumado" ou "Tentado" apenas se explícito; senão deixar em branco.
    - Latrocínio → "Consumado".
    - Morte por causas naturais → deixar em branco.

Promoção de arquivamento:
{document}
"""

prompt_inquerito_e_envolvidos = """
Você é um assistente especializado em analisar promoções de arquivamento e extrair, de forma conjunta:

- Informações estruturadas do inquérito
- Informações estruturadas sobre vítimas, suspeitos/investigados e testemunhas

Instruções Gerais:
- Utilize apenas informações explicitamente presentes no texto.
- Não invente dados e não utilize "não informado".
- Campos sem informação devem permanecer em branco.
- Preserve datas e trechos literais.
- Não inclua explicações.

Classificação do Crime:
- Homicídio, Latrocínio ou Morte por causas naturais.
- Não use "Morte por causas naturais" se houver suspeitos ligados à morte.

Regras do inquérito:
- **razao_arquivamento** deve ser trecho literal.
- **é_feminicidio** apenas se for Homicídio.
- **bem_roubado** apenas se for Latrocínio.
- **resultado**:
    - Homicídio → preencher apenas se explícito.
    - Latrocínio → "Consumado".
    - Morte por causas naturais → deixar em branco.

Regras para Pessoas:
- Inferir sexo pelo nome quando necessário.
- **é_policial** só pode ser True se a corporação estiver explicitamente descrita.
- Se não houver corporação explícita → **é_policial=False** e **corporacao_policial** em branco.
- **armada** só pode ser True se a arma estiver explicitamente descrita; caso contrário, deixar em branco.

Promoção de arquivamento:
{document}
"""

prompt_tudo_em_um = """
Você é um assistente especializado em analisar promoções de arquivamento e extrair todas as informações estruturadas do inquérito e dos envolvidos.

Instruções:
- Utilize apenas informações explicitamente presentes no texto.
- Não invente dados e não utilize "não informado".
- Campos sem informação devem permanecer em branco.
- Preserve trechos literais.
- Não inclua explicações.

Classifique o crime como:
- Homicídio
- Latrocínio
- Morte por causas naturais
Não use "Morte por causas naturais" se houver suspeitos ligados à morte.

Regras:
- **razao_arquivamento** deve ser literal.
- **é_feminicidio** apenas se for Homicídio.
- **bem_roubado** apenas se for Latrocínio.
- **resultado**:
    - Homicídio → preencher apenas se explícito.
    - Latrocínio → "Consumado".
    - Morte por causas naturais → deixar em branco.
- Inferir sexo pelo nome quando necessário.

Regras Campos:
- Nunca marque **é_policial** como true se o texto não afirmar explicitamente que a pessoa é policial.
- Se **é_policial** for true, **corporacao_policial** deve estar explícita, do contrário deve ser false.
- Nunca marque **armada** como true se o texto não mencionar arma.

Promoção de arquivamento:
{document}
"""