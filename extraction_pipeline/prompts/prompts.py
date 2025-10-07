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
Você é um assistente especializado em analisar promoções de arquivamento e extrair informações estruturadas sobre os suspeitos/investigados.  
Siga cuidadosamente as instruções abaixo:

Instruções:
- Extraia **apenas informações sobre os suspeitos/investigados** mencionadas no documento.
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

prompt_inquerito_info = """
Você é um assistente especializado em analisar promoções de arquivamento e extrair informações estruturadas.
Sua tarefa é extrair duas categorias principais de informação: 
1) Um mapeamento de todas as pessoas envolvidas e seus respectivos papéis.
2) Os detalhes sobre o inquérito policial.

Siga cuidadosamente todas as instruções abaixo.

Instruções Gerais:
- Sua resposta deve seguir o schema de saída.
- Caso alguma informação não esteja disponível, não preencha o respectivo campo. Não invente dados e não preencha com "não informado".

Instruções para o mapeamento de 'pessoas_envolvidas':
- Identifique o nome completo de todas as vítimas, suspeitos/investigados e testemunhas mencionados no texto.
- Preencha as listas `vitimas`, `suspeitos_investigados` e `testemunhas` com os nomes correspondentes.
- Seja cuidadoso para não classificar a mesma pessoa em múltiplos papéis, a menos que o texto explicitamente suporte isso.

Instruções para os detalhes do 'inquerito':
- Para datas e horas, mantenha o formato exato encontrado no documento.
- Para o campo 'razao_arquivamento', copie textualmente o trecho do documento que justifica o arquivamento, sem resumir ou interpretar.
- As seguintes regras de negócio **devem** ser seguidas:
    - O campo 'é_feminicidio' só pode ser True se a 'classificacao_crime' for Homicídio.
    - O campo 'bem_roubado' deve ser preenchido se a 'classificacao_crime' for Latrocínio.
    - O campo 'resultado' segue uma lógica específica: Latrocínio é sempre 'CONSUMADO'. Para 'MORTE_SEM_INDICIO_DE_CRIME', o resultado deve ser nulo (não preenchido).

Promoção de arquivamento:
{document}
"""