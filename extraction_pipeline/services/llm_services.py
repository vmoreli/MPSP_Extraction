import os
import json
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
from google import genai
from extraction_pipeline.config import PRECOS, MODEL

# ============================================================
# CONFIGURAÇÕES E CLIENTES
# ============================================================

# Carrega variáveis do .env
load_dotenv()

# Inicializa clients
try:
    client_openai = OpenAI(
        api_key=os.environ["MARITACA_API_KEY"],
        base_url="https://chat.maritaca.ai/api"
    )
    client_gemini = genai.Client()
except KeyError:
    raise EnvironmentError("A variável de ambiente 'MARITACA_API_KEY' não foi encontrada. Configure-a no arquivo .env.")

# Contador global de tokens e custo
TOKEN_USAGE = {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
    "total_cost_brl": 0.0
}


def call_llm(
    prompt: str,
    output_schema: BaseModel,
    model_name: str = None
) -> BaseModel:
    """
    Faz uma chamada ao modelo LLM (Sabiazinho/Maritaca ou Gemini)
    e contabiliza uso de tokens e custo em reais.

    Args:
        prompt (str): Texto de entrada.
        output_schema (BaseModel): Classe Pydantic com o formato esperado da saída.
        model_name (str): Nome do modelo (opcional, usa o importado de config por padrão).

    Returns:
        BaseModel: Instância(s) de output_schema com os dados estruturados.
    """
    model_name = model_name or MODEL
    print(f"Chamando o modelo {model_name}...")

    # ============================================================
    # MODELOS SABIAZINHO / MARITACA
    # ============================================================
    if not model_name.lower().startswith("gemini"):
        messages = [{"role": "user", "content": prompt}]

        response = client_openai.beta.chat.completions.parse(
            model=model_name,
            messages=messages,
            response_format=output_schema,
            temperature=0.0,
        )

        # Tokens e custo
        if hasattr(response, "usage") and response.usage:
            usage = response.usage
            prompt_tokens = usage.prompt_tokens or 0
            completion_tokens = usage.completion_tokens or 0
            total_tokens = usage.total_tokens or (prompt_tokens + completion_tokens)

            TOKEN_USAGE["prompt_tokens"] += prompt_tokens
            TOKEN_USAGE["completion_tokens"] += completion_tokens
            TOKEN_USAGE["total_tokens"] += total_tokens

            preco_modelo = PRECOS.get(model_name, {"in": 0, "out": 0})
            preco_in = preco_modelo["in"]
            preco_out = preco_modelo["out"]

            # custo em reais (por milhão de tokens)
            input_cost = (prompt_tokens * preco_in) / 1_000_000
            output_cost = (completion_tokens * preco_out) / 1_000_000
            TOKEN_USAGE["total_cost_brl"] += input_cost + output_cost

            print(f"✅ Tokens usados: {total_tokens:,} | Custo acumulado: R${TOKEN_USAGE['total_cost_brl']:.4f}")
        else:
            print("⚠️ Não foi possível extrair metadados de uso de tokens da resposta.")

        return response.choices[0].message.parsed

    # ============================================================
    # MODELOS GEMINI
    # ============================================================
    else:
        response = client_gemini.models.generate_content(
            model=model_name,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": output_schema,
            },
        )

        parsed_output = response.parsed

        # Tokens e custo
        if hasattr(response, "usage_metadata"):
            usage = response.usage_metadata
            prompt_tokens = usage.prompt_token_count or 0
            completion_tokens = usage.candidates_token_count or 0
            total_tokens = usage.total_token_count or (prompt_tokens + completion_tokens)

            TOKEN_USAGE["prompt_tokens"] += prompt_tokens
            TOKEN_USAGE["completion_tokens"] += completion_tokens
            TOKEN_USAGE["total_tokens"] += total_tokens

            preco_modelo = PRECOS.get(model_name, {"in": 0, "out": 0})
            preco_in = preco_modelo["in"]
            preco_out = preco_modelo["out"]

            input_cost = (prompt_tokens * preco_in) / 1_000_000
            output_cost = (completion_tokens * preco_out) / 1_000_000
            TOKEN_USAGE["total_cost_brl"] += input_cost + output_cost

            print(f"✅ Tokens usados: {total_tokens:,} | Custo acumulado: R${TOKEN_USAGE['total_cost_brl']:.4f}")
        else:
            print("⚠️ Não foi possível extrair metadados de uso de tokens da resposta.")

        if isinstance(parsed_output, list):
            print(f"✅ Gemini retornou {len(parsed_output)} item(s).")
        else:
            print("✅ Gemini retornou um único objeto estruturado.")

        return parsed_output
