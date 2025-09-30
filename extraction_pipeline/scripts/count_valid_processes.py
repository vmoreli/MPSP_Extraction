import json
from pathlib import Path
from typing import List, Set
from maritalk import count_tokens as maritalk_count_tokens
from dotenv import load_dotenv
import google.generativeai as genai

# Importando paths
from extraction_pipeline.config import (
    ATTACHMENTS_DIR,
    FILTERS_DIR,
    MODEL,
    PRECOS
)
JSON_PATH = "output/run_2025-09-29_22-56-29/sabiazinho-3.0"

# Importando prompts
from extraction_pipeline.prompts.prompts import (
    prompt_vitimas,
    prompt_testemunhas,
    prompt_suspeitos,
    prompt_inquerito_info
)

# Importando schemas
from extraction_pipeline.graphs.extract_data import (
    InqueritoTotal
)

# --- CONFIGURAÇÃO ---
# Lista de exclusão são processos cujos txt's foram avaliados e descobriu que ocorreram erros no parsing dos documentos originais
EXCLUSION_FILES: List[Path] = [
    FILTERS_DIR / "outliers_bottom_1_percent.json", # Processos com poucos tokens
    FILTERS_DIR / "outliers_top_1_percent.json"     # Procesos com muitos tokens
]

# Lista de inclusão são os processos que passaram pelo filtro do 'assunto' para somente homicídio e similares
INCLUSION_FILES: List[Path] = [
    FILTERS_DIR / "processes_passed_filter.json"
]

# Se está na lista de inclusão mas não foi encontrado em disco, é pq não tem promoção de arquivamento disponível
# Se tem pasta do processo em disco mas não tem txt, é pq não foi possível fazer o parsing da promoção de arquivamento

# Para simular o modo de avaliação do seu script original
EVAL_MODE = False
EVAL_PATH = FILTERS_DIR / "ids_eval.json"

# --- Funções Auxiliares ---

def get_token_count(text: str, model_name: str) -> int:
    """
    Conta os tokens de um texto usando o tokenizador apropriado 
    para a família do modelo (Maritalk ou Gemini).
    """
    if model_name.startswith("gemini"):
        # Para modelos Gemini, usamos a biblioteca do Google
        # O modelo é instanciado aqui para garantir que estamos usando o correto
        try:
            model = genai.GenerativeModel(model_name)
            return model.count_tokens(text).total_tokens
        except Exception as e:
            print(f"Erro ao contar tokens com Gemini para o modelo '{model_name}': {e}")
            return 0
    elif "sabia" in model_name:
        # Para modelos Maritalk, usamos a biblioteca original
        return maritalk_count_tokens(text, model_name)
    else:
        # Lança um erro se um modelo não suportado for passado
        raise ValueError(f"Modelo '{model_name}' não suportado para contagem de tokens.")

def load_ids_from_json_files(file_paths: List[Path]) -> Set[str]:
    """
    Carrega IDs de arquivos JSON, lidando com múltiplos formatos:
    1. Dicionário: { "id1": valor, "id2": valor, ... } -> extrai as chaves.
    2. Lista de Objetos: [ { "NumMP": id1 }, { "NumMP": id2 }, ... ] -> extrai o valor de "NumMP".
    3. Lista Simples: [ "id1", "id2", ... ] -> extrai os elementos.
    """
    all_ids = set()
    if not file_paths:
        return all_ids

    for file_path in file_paths:
        if not file_path.exists():
            print(f"Aviso: O arquivo de filtro '{file_path}' não foi encontrado.")
            continue
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # --- LÓGICA DE EXTRAÇÃO INTELIGENTE ---
            if isinstance(data, dict):
                # Formato 1: As chaves do dicionário são os IDs
                all_ids.update(map(str, data.keys()))
            elif isinstance(data, list):
                if not data:  # Pula listas vazias
                    continue
                
                # Verifica o tipo do primeiro elemento para decidir a estratégia
                if isinstance(data[0], dict):
                    # Formato 2: Lista de objetos com a chave "NumMP"
                    for item in data:
                        if isinstance(item, dict) and "NumMP" in item and item["NumMP"] is not None:
                            all_ids.add(str(item["NumMP"]))
                else:
                    # Formato 3: Lista simples de IDs
                    all_ids.update(map(str, data))
            else:
                print(f"Aviso: Formato JSON não suportado em '{file_path.name}'. O conteúdo deve ser uma lista ou um dicionário.")

        except json.JSONDecodeError:
            print(f"Erro: Falha ao decodificar JSON do arquivo '{file_path}'.")
        except Exception as e:
            print(f"Erro ao ler o arquivo '{file_path}': {e}")
            
    return all_ids

def extrair_texto_do_json(data: dict) -> str:
    """
    Converte o objeto JSON inteiro (dicionário ou lista) em uma string 
    formatada para a contagem de tokens.
    """
    # Converte o objeto Python de volta para uma string JSON formatada
    return json.dumps(data, ensure_ascii=False, indent=2)

def analisar_media_tokens_json(model_name: str, json_dir: Path = Path(JSON_PATH)):
    """
    Analisa um diretório com arquivos JSON, calcula o total de tokens
    e a média de tokens por arquivo.
    """
    print("\n--- Análise de Média de Tokens em Arquivos JSON ---")
    if not json_dir.is_dir():
        print(f"Erro: O diretório de JSONs '{json_dir}' não foi encontrado.")
        return

    # Usa o glob para encontrar todos os arquivos .json na estrutura de subdiretórios
    glob_pattern = "*/*/*.json"
    json_files = list(json_dir.glob(glob_pattern))
    
    if not json_files:
        print(f"Nenhum arquivo .json encontrado na estrutura '{glob_pattern}' dentro de '{json_dir}'.")
        return

    total_tokens = 0
    arquivos_processados = 0
    
    print(f"Encontrados {len(json_files)} arquivos .json. Iniciando contagem de tokens...")

    # Itera sobre os arquivos encontrados
    for file_path in json_files:
        try:
            with file_path.open('r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Extrai o texto usando a função auxiliar (agora fazendo o dump)
            texto_para_tokenizar = extrair_texto_do_json(json_data)
            
            if texto_para_tokenizar:
                total_tokens += get_token_count(texto_para_tokenizar, model_name)
                arquivos_processados += 1
            # Não precisa mais de aviso, pois o dump de um json vazio é só "{}"

        except json.JSONDecodeError:
            print(f"Aviso: Falha ao decodificar JSON no arquivo {file_path}")
        except Exception as e:
            print(f"Erro ao processar o arquivo {file_path}: {e}")

    # Calcula e exibe os resultados
    if arquivos_processados > 0:
        media_tokens = total_tokens / arquivos_processados
        print("\n--- Resultado da Análise de JSONs ---")
        print(f"Total de Arquivos JSON Processados: {arquivos_processados}")
        print(f"Total de Tokens Calculados (do JSON inteiro): {total_tokens:,}")
        print(f"Média de Tokens por Arquivo JSON: {media_tokens:,.0f}")

        return media_tokens
    else:
        print("\nNenhum arquivo JSON válido foi processado.")


def analyze_dataset_counts(model_name: str):
    """
    Executa a análise e imprime um relatório explicativo.
    """
    print("--- Relatório de Análise do Conjunto de Dados para Pipeline de Extração ---")

    # 1. Análise do Diretório Base
    if not ATTACHMENTS_DIR.is_dir():
        print(f"Erro: O diretório de anexos '{ATTACHMENTS_DIR}' não existe.")
        return

    print("\n--- 1. O Universo de Dados Disponíveis ---")
    print("Analisando o diretório de attachments...")
    glob_pattern = "*/*"
    all_process_paths = [path for path in ATTACHMENTS_DIR.glob(glob_pattern) if path.is_dir()]
    if not all_process_paths:
        all_process_paths = [d for d in ATTACHMENTS_DIR.iterdir() if d.is_dir()]
        if not all_process_paths:
             print("Erro: Nenhum diretório de processo encontrado.")
             return

    # Mapeia ID para Path para acesso rápido depois
    id_to_path = {p.name: p for p in all_process_paths}
    all_process_ids = set(id_to_path.keys())
    process_ids_with_txt = {p.name for p in all_process_paths if any(p.glob('*.txt'))}
    total_on_disk = len(all_process_ids)
    total_with_txt = len(process_ids_with_txt)

    print(f"\n- Total de processos com documentos baixados (pastas existentes): {total_on_disk}")
    print(f"- Desses, {total_with_txt} tiveram o parsing inicial bem-sucedido (geraram um arquivo .txt).")
    print("  (Significa que o documento \"promoção de arquivamento\" foi extraído com sucesso)")
    print(f"- E {total_on_disk - total_with_txt} falharam no parsing inicial (não geraram .txt).")
    print("  (O documento pode estar corrompido, em branco ou em formato não suportado)")

    # 2. Carregar filtros e diagnosticar cobertura
    print("\n--- 2. Critérios de Filtragem e Diagnóstico de Cobertura ---")
    inclusion_ids = load_ids_from_json_files([EVAL_PATH] if EVAL_MODE and EVAL_PATH.exists() else INCLUSION_FILES)
    exclusion_ids = load_ids_from_json_files(EXCLUSION_FILES)
    
    print("\n[+] Universo de Interesse (Inclusão):")
    print("    Processos filtrados por assunto (homicídio e similares).")
    print(f"    - Total de {len(inclusion_ids)} processos de interesse encontrados no arquivo de filtro.")
    found_inclusion_count = len(all_process_ids.intersection(inclusion_ids))
    missing_inclusion_count = len(inclusion_ids) - found_inclusion_count
    print(f"    - Desses, {found_inclusion_count} foram encontrados no disco (têm uma pasta correspondente).")
    print(f"    - DIAGNÓSTICO: Os {missing_inclusion_count} restantes não foram encontrados, o que significa que não possuem uma \"promoção de arquivamento\" disponível para análise.")

    print("\n[-] Lista de Exclusão:")
    print("    Processos com erros de parsing conhecidos (outliers de tokens).")
    print(f"    - Total de {len(exclusion_ids)} processos a serem explicitamente ignorados.")
    found_exclusion_count = len(all_process_ids.intersection(exclusion_ids))
    print(f"    - Desses, {found_exclusion_count} estão presentes no conjunto de dados baixado e seriam removidos se encontrados no universo de interesse.")
    
    # 3. Simulação
    print("\n--- 3. Simulação do Pipeline: Qual o Resultado Final? ---")
    runnable_ids = all_process_ids.intersection(inclusion_ids)
    print(f"\n1. Ponto de Partida: Começamos com os {len(runnable_ids)} processos de interesse que efetivamente possuem uma pasta no disco.")
    excluded_count = len(runnable_ids.intersection(exclusion_ids))
    runnable_ids.difference_update(exclusion_ids)
    print(f"2. Aplicando Exclusões: Deste grupo, removemos {excluded_count} processos que estão na lista de exclusão por conterem erros de parsing (outliers).")
    print(f"3. Resultado: Sobram {len(runnable_ids)} processos válidos e de interesse para serem executados pelo pipeline.")

    # 4. Sumário Executivo e Contagem de Tokens
    print("\n--- 4. Sumário Executivo e Insights ---")
    final_runnable_with_txt_ids = runnable_ids.intersection(process_ids_with_txt)
    final_runnable_with_txt_count = len(final_runnable_with_txt_ids)
    final_runnable_no_txt_count = len(runnable_ids) - final_runnable_with_txt_count
    
    print("\n+------------------------------------------------------+")
    print(f"| NÚMERO FINAL DE PROCESSOS A SEREM EXECUTADOS (COM TXT): {final_runnable_with_txt_count:<5} |")
    print("+------------------------------------------------------+")
    print(f"  - {final_runnable_with_txt_count} processos com parsing bem-sucedido (possuem algum .txt).")
    print(f"  - {final_runnable_no_txt_count} processos que falharam no parsing (não possuem nenhum .txt).")

    # Contagem de tokens
    total_tokens = 0        # tokens de documentos
    prompt_tokens = 0       # tokens de prompts
    schemas_tokens = 0      # tokens de schemas
    if final_runnable_with_txt_count > 0:
        print(f"\n--- Análise de Custo/Volume (para os {final_runnable_with_txt_count} processos com .txt) ---")
        print("Calculando tokens...")
        for process_id in final_runnable_with_txt_ids:
            proc_path = id_to_path[process_id]
            # Pega o primeiro arquivo .txt que encontrar no diretório
            txt_file = next(proc_path.glob('*.txt'), None)
            if txt_file:
                try:
                    content = txt_file.read_text(encoding='utf-8', errors='ignore')
                    total_tokens += get_token_count(content, model_name)
                except Exception as e:
                    print(f"Aviso: Não foi possível ler ou contar tokens do arquivo {txt_file}. Erro: {e}")
        
        average_tokens = total_tokens / final_runnable_with_txt_count
        print(f"  - Total de Tokens a Serem Processados: {total_tokens:,}")
        print(f"  - Média de Tokens por Documento: {average_tokens:,.0f}")

    prompt_tokens = (
        get_token_count(prompt_vitimas, model_name) + 
        get_token_count(prompt_inquerito_info, model_name) + 
        get_token_count(prompt_suspeitos, model_name) + 
        get_token_count(prompt_testemunhas, model_name)
    )

    schemas_tokens = get_token_count(json.dumps(InqueritoTotal.model_json_schema(), indent=2, ensure_ascii=False), model_name)
    print(f"  - Total de tokens nos 4 prompts: {prompt_tokens:,.0f}")
    print(f"  - Total de tokens nos 4 schemas: {schemas_tokens:,.0f}")
    

    print("\n[!] INSIGHTS ACIONÁVEIS:")
    print(f"1.  FALHA DE PARSING: Existem {final_runnable_no_txt_count} processos de interesse (homicídio) que foram baixados mas falharam no parsing. Estes podem ser investigados para recuperação.")
    print(f"2.  DADOS INDISPONÍVEIS: Existem {missing_inclusion_count} processos de interesse que não puderam ser analisados por falta do documento \"promoção de arquivamento\".")
    print(f"3.  QUALIDADE DE DADOS: O pipeline irá ignorar ativamente {excluded_count} processos de interesse devido a problemas de qualidade (outliers de tokens) previamente identificados.")

    print("\n--- Análise Concluída ---")

    total_tokens_in = total_tokens + final_runnable_with_txt_count * (prompt_tokens + schemas_tokens)
    return total_tokens_in, final_runnable_with_txt_count
    

if __name__ == '__main__':
    load_dotenv()

    # Lista de modelos que você quer analisar
    models_to_analyze = ["sabiazinho-3.0", "sabia-3.0", "gemini-2.5-flash", "gemini-2.5-pro"]

    # Dicionário para armazenar os resultados de cada modelo
    results = {}

    # --- Executa a análise para cada modelo ---
    for model in models_to_analyze:
        print(f"\n{'='*20} ANALISANDO MODELO: {model.upper()} {'='*20}")
        try:
            total_tokens_in, num_files = analyze_dataset_counts(model_name=model)
            media_tokens_out = analisar_media_tokens_json(model_name=model)
            
            if media_tokens_out is not None and num_files > 0:
                total_tokens_out = media_tokens_out * num_files
                results[model] = {
                    "tokens_in": total_tokens_in,
                    "tokens_out": total_tokens_out
                }
            else:
                print(f"Não foi possível calcular os tokens de saída para o modelo {model}.")
                results[model] = None

        except ValueError as e:
            print(f"Erro ao analisar o modelo {model}: {e}")
        except Exception as e:
            print(f"Ocorreu um erro inesperado ao processar o modelo {model}: {e}")

    # --- Imprime o relatório de custos comparativo ---
    print(f"\n\n{'='*20} RELATÓRIO DE CUSTOS COMPARATIVO {'='*20}")
    
    for model, data in results.items():
        if data is None:
            print(f"\n--- {model.upper()} ---")
            print("Cálculo de custo não disponível.")
            continue

        tokens_in = data["tokens_in"]
        tokens_out = data["tokens_out"]
        
        # Pega os preços do dicionário de configuração
        model_prices = PRECOS.get(model)
        if not model_prices:
            print(f"Aviso: Preços para o modelo '{model}' não encontrados no arquivo de configuração.")
            continue

        custo_in = (tokens_in / 1_000_000) * model_prices["in"]
        custo_out = (tokens_out / 1_000_000) * model_prices["out"]
        custo_total = custo_in + custo_out
        
        print(f"\n--- PREVISÃO DE CUSTO PARA: {model.upper()} ---")
        print(f"  - Tokens de Entrada : {tokens_in:,.0f}")
        print(f"  - Tokens de Saída   : {tokens_out:,.0f}")
        print(f"  - Custo Entrada (IN): R$ {custo_in:,.2f}")
        print(f"  - Custo Saída (OUT) : R$ {custo_out:,.2f}")
        print(f"  - CUSTO TOTAL       : R$ {custo_total:,.2f}")
        
    print(f"\n{'='*65}")