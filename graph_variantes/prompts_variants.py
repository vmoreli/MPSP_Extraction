# -*- coding: utf-8 -*-

"""
Prompts variants oficiais do experimento.
"""

# ==========================================
# PROMPTS INDIVIDUAIS (BASE)
# ==========================================

prompt_vitimas = """
Você é um assistente especializado em analisar promoções de arquivamento e extrair informações estruturadas sobre as vítimas.  
Siga cuidadosamente as instruções abaixo:  

Instruções:
- Extraia **apenas informações sobre as vítimas** mencionadas no documento.  
- Quando o sexo da vítima não for explicitamente informado, **infira pelo nome**.  
- Caso alguma informação não esteja disponível, não preencha o respectivo campo. Não invente dados e não preencha com "não informado".  
- O que for "não informado" não precisa ser preenchido.
- Sua resposta deve seguir **exatamente** o schema completo definido para vítimas. 

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
- O que for "não informado" não precisa ser preenchido.
- Sua resposta deve seguir **exatamente** o schema completo definido para suspeitos.


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

Instruções Específicas:
- Classifique o crime conforme o conteúdo do texto (Homicídio, Latrocínio, ou Morte por causas naturais).
- Considere como **Morte por causas naturais** apenas aquelas que não decorrem da ação de suspeitos/investigados.
- O campo `razao_arquivamento` deve conter o **trecho literal** que justifica o arquivamento, sem resumo ou interpretação.
- As seguintes regras de negócio **devem ser respeitadas**:
    - O campo `é_feminicidio` só pode ser `True` se a classificação do crime for **Homicídio**.
    - O campo `bem_roubado` deve ser preenchido apenas se a classificação for **Latrocínio**.
    - O campo `resultado` segue a lógica:
        - **Latrocínio** → sempre `CONSUMADO`
        - **Morte por causas naturais** → campo em branco


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

# ==========================================
# PROMPTS COMBINADOS (REFATORADOS)
# ==========================================

prompt_envolvidos_vst = """
Você é um assistente especializado em analisar promoções de arquivamento e extrair, de forma conjunta, informações estruturadas sobre: Vítimas, Suspeitos/Investigados e Testemunhas.

Instruções Gerais:
- Extraia **apenas informações explícitas** no documento.
- Caso alguma informação não esteja disponível, não preencha o respectivo campo. Não invente dados e não preencha com "não informado" (o que for "não informado" não precisa ser preenchido).
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
- Identifique todas as pessoas (vítimas, suspeitos/investigados ou testemunhas) usando nomes completos sempre que disponíveis.
- Classifique o crime como Homicídio, Latrocínio, ou Morte por causas naturais.
- **Importante**: Um inquérito que tenha suspeitos ligados à morte não pode ser classificado como "Morte por causas naturais".

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
- Campos sem informação devem permanecer em branco. O que for "não informado" não precisa ser preenchido.
- Preserve datas, horários e trechos literais exatamente como aparecem.

Regras para Pessoas (Vítimas, Suspeitos, Testemunhas):
- **Sexo**: Quando não explícito, infira pelo nome.
- **é_policial**: Só marque como `True` se a corporação estiver explicitamente descrita. Se `True`, preencha `corporacao_policial`. Se `False`, deixe em branco.
- **armada (Vítimas)**: Só marque como `True` se a arma estiver explicitamente descrita. Se `True`, preencha `arma_da_vítima`.

Regras para Inquérito:
- Classifique o crime (Homicídio, Latrocínio ou Morte por causas naturais). Não use "Morte por causas naturais" se houver suspeitos.
- `razao_arquivamento`: Deve ser o trecho literal do documento.
- `é_feminicidio`: Apenas se for **Homicídio**.
- `bem_roubado`: Apenas se for **Latrocínio**.
- `resultado`: "Consumado" ou "Tentado" (se Homicídio e explícito), "Consumado" (se Latrocínio), ou em branco (se Morte por causas naturais).

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
- Campos sem informação devem permanecer em branco. O que for "não informado" não precisa ser preenchido.
- Preserve trechos literais (como a razão de arquivamento) exatamente como aparecem.

Regras para Mapeamento e Inquérito:
- Classifique como Homicídio, Latrocínio ou Morte por causas naturais. Não use "Morte por causas naturais" se houver suspeitos ligados à morte.
- `é_feminicidio`: Preencher `True` apenas se for **Homicídio**.
- `bem_roubado`: Preencher apenas se for **Latrocínio**.
- `resultado`: Preencher em Homicídio apenas se explícito, fixar "Consumado" em Latrocínio, e deixar em branco para Morte por causas naturais.

Regras para Pessoas (Envolvidos):
- **Sexo**: Quando não explícito, infira pelo nome.
- **é_policial**: Só marque `True` se a corporação estiver explícita (e preencha `corporacao_policial`).
- **armada (Vítimas)**: Só marque `True` se o texto mencionar a arma (e preencha `arma_da_vítima`).

Promoção de arquivamento:
{document}
"""