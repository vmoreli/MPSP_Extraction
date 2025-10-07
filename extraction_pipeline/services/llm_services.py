import os
import json
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv
from google import genai

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configuração do Cliente e Custos ---

# Preços por milhão de tokens SUBSTITUIR COM VALORES CORRETOS
PRECO_INPUT_SABIAZINHO_USD_POR_M_TOKENS = 0.20
PRECO_OUTPUT_SABIAZINHO_USD_POR_M_TOKENS = 0.40

# Inicializa clients necessários
try:
    # Client OpenAI/MaritacaAI
    client_openai = OpenAI(
        api_key=os.environ["MARITACA_API_KEY"],
        base_url="https://chat.maritaca.ai/api"
    )

    # Client gemini
    client_gemini = genai.Client()
except KeyError:
    raise EnvironmentError("A variável de ambiente 'MARITACA_API_KEY' não foi encontrada. Por favor, configure-a.")

# Contador global de tokens e custo
TOKEN_USAGE = {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
    "total_cost_usd": 0.0
}


def call_llm(
        prompt: str,
        output_schema: BaseModel,
        model_name: str = "sabiazinho-3"
) -> BaseModel:
    """
    Faz uma chamada a um modelo LLM (Sabiazinho da Maritaca ou Gemini da Google)
    para extrair dados estruturados e contabiliza o uso de tokens e custo.

    Args:
        prompt (str): O texto de entrada.
        output_schema (BaseModel): Classe Pydantic que define o formato esperado da saída.
        model_name (str): Nome do modelo (ex: "sabiazinho-3" ou "gemini-2.5-flash").

    Returns:
        BaseModel: Instância de output_schema (ou lista de instâncias) com os dados extraídos.
    """
    print(f"Chamando o modelo {model_name}...")
    
    # Chamada para modelos da Maritaca AI ou OpenAI
    if not model_name.lower().startswith("gemini"):
        # A API da OpenAI/Maritaca usa uma lista de mensagens
        messages = [
            {"role": "user", "content": prompt}
        ]

        # O método 'parse' da biblioteca da OpenAI lida com a formatação e validação do JSON
        response = client_openai.beta.chat.completions.parse(
            model=model_name,
            messages=messages,
            response_format=output_schema,
            temperature=0.0, # Temperatura baixa para saídas mais consistentes
        )
        
        # Coleta o uso de tokens do objeto de resposta
        if hasattr(response, "usage") and response.usage:
            usage = response.usage
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens

            # Atualiza o dicionário global de uso de tokens
            TOKEN_USAGE["prompt_tokens"] += prompt_tokens
            TOKEN_USAGE["completion_tokens"] += completion_tokens
            TOKEN_USAGE["total_tokens"] += total_tokens

            # Calcula o custo da chamada atual
            input_cost = prompt_tokens * (PRECO_INPUT_SABIAZINHO_USD_POR_M_TOKENS / 1_000_000)
            output_cost = completion_tokens * (PRECO_OUTPUT_SABIAZINHO_USD_POR_M_TOKENS / 1_000_000)
            
            # Atualiza o custo total acumulado
            TOKEN_USAGE["total_cost_usd"] += (input_cost + output_cost)
            print("Chamada concluída com sucesso!")
        else:
            print("Não foi possível encontrar os metadados de uso de tokens na resposta.")
        
        response_content = response.choices[0].message.content

        return response_content
    
    else:
        # Retorno estruturado conforme o schema Pydantic
        response = client_gemini.models.generate_content(
            model=model_name,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": output_schema,
            },
        )

        # O .parsed já devolve instância(s) do Pydantic
        parsed_output = response.parsed

        # Exibe log informativo
        if isinstance(parsed_output, list):
            print(f"✅ Gemini retornou {len(parsed_output)} item(s).")
        else:
            print("✅ Gemini retornou um único objeto estruturado.")

        # Coleta o uso de tokens
        if hasattr(response, "usage_metadata"):
            usage = response.usage_metadata
            prompt_tokens = usage.prompt_token_count
            completion_tokens = usage.candidates_token_count
            total_tokens = usage.total_token_count

            # Atualiza o dicionário de uso de tokens
            TOKEN_USAGE["prompt_tokens"] += prompt_tokens
            TOKEN_USAGE["completion_tokens"] += completion_tokens
            TOKEN_USAGE["total_tokens"] += total_tokens

            # Calcula o custo em dólares usando os novos valores
            input_cost = prompt_tokens * 0.30 / 1_000_000    # $0.30 por 1M tokens de entrada
            output_cost = completion_tokens * 2.50 / 1_000_000  # $2.50 por 1M tokens de saída
            total_cost = input_cost + output_cost

            # Atualiza o custo total acumulado
            TOKEN_USAGE["total_cost_usd"] += total_cost
            
        return parsed_output

