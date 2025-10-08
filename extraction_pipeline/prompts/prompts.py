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