import argparse
import json
import sys
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List

# --- Importação dos Schemas Base ---
try:
    from extraction_pipeline.schemas.extract_data_schemas import (
        ResumoProcesso, 
        Vitima, 
        Pessoa, 
        Inquerito
    )
except ImportError:
    print(
        "Erro: Não foi possível encontrar o arquivo 'schemas.py'.\n"
        "Certifique-se de que o arquivo 'schemas.py' com todas as definições "
        "(Pessoa, Vitima, Inquerito, etc.) esteja no mesmo diretório.",
        file=sys.stderr
    )
    sys.exit(1)

class InqueritoTotal(BaseModel):
    """
    Modelo unificado para extração, corrigido para aceitar listas diretas 
    de vítimas, suspeitos e testemunhas.
    """
    resumo_processo: ResumoProcesso = Field(
        description="Mapeamento dos envolvidos e classificação do tipo de crime."
    )
    vitimas: Optional[List[Vitima]] = Field(
        None, description="Informações sobre as vítimas"
    )
    suspeitos: Optional[List[Pessoa]] = Field(
        None, description="Informações sobre os autores"
    )
    testemunhas: Optional[List[Pessoa]] = Field(
        None, description="Informações sobre as testemunhas"
    )
    inquerito: Optional[Inquerito] = Field(
        None, description="Informações gerais do inquérito"
    )

    # Configuração para permitir campos extras no JSON que não estão no schema
    class Config:
        extra = 'ignore'

def formatar_erros(erros: list) -> str:
    """Formata a lista de erros da Pydantic para uma leitura mais clara."""
    mensagens = []
    for erro in erros:
        # 'loc' é a localização do erro (ex: ['vitimas', 0, 'faleceu'])
        localizacao = " -> ".join(map(str, erro['loc']))
        mensagens.append(f"  - Campo: {localizacao} | Erro: {erro['msg']}")
    return "\n".join(mensagens)

def validar_json_inqueritos(arquivo_path: Path):
    """
    Lê um arquivo JSON e valida cada objeto de nível superior 
    contra o schema InqueritoTotal (corrigido).
    """
    if not arquivo_path.is_file():
        print(f"Erro: Arquivo não encontrado em '{arquivo_path}'", file=sys.stderr)
        sys.exit(1)

    print(f"Iniciando validação do arquivo: {arquivo_path.name}...")

    try:
        with open(arquivo_path, 'r', encoding='utf-8') as f:
            dados = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Erro: O arquivo não é um JSON válido. {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Erro ao ler o arquivo: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(dados, dict):
        print(f"Erro: O JSON não é um dicionário (objeto) no nível raiz.", file=sys.stderr)
        sys.exit(1)

    processos_invalidos = {}
    total_validos = 0
    total_processados = 0

    for chave_processo, objeto_inquerito in dados.items():
        total_processados += 1
        try:
            # Tenta validar o objeto aninhado
            InqueritoTotal.model_validate(objeto_inquerito)
            total_validos += 1
        except ValidationError as e:
            # Armazena a chave do processo e a razão formatada da falha
            processos_invalidos[chave_processo] = formatar_erros(e.errors())
        except Exception as e:
            # Captura outros erros inesperados (ex: não é um dict)
            processos_invalidos[chave_processo] = f"  - Erro inesperado: {str(e)}"

    # --- Impressão do Relatório ---
    print("\n========= Relatório da Validação =========")
    print(f"Total de processos processados: {total_processados}")
    print(f"Total de processos VÁLIDOS: {total_validos}")
    print(f"Total de processos INVÁLIDOS: {len(processos_invalidos)}")
    print("========================================\n")

    if processos_invalidos:
        print("--- Detalhes dos Processos Inválidos ---")
        for chave, motivo in processos_invalidos.items():
            print(f"\n[FALHA] Processo: {chave}")
            print("Motivo(s):")
            print(motivo)
        
        print("\nValidação falhou.")
        sys.exit(1) # Termina com código de erro
    else:
        print("[SUCESSO] Todos os processos no arquivo são válidos.")
        sys.exit(0) # Termina com sucesso

# --- Bloco de Execução ---
if __name__ == "__main__":
    INPUT_JSON = "output_normalizado.json" 

    caminho_arquivo = Path(INPUT_JSON)
    
    validar_json_inqueritos(caminho_arquivo)