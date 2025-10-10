import json
import os
from pathlib import Path
from typing import List, Set

from dotenv import load_dotenv
import google.generativeai as genai
from maritalk import count_tokens as maritalk_count_tokens

# Importando paths do seu projeto (ajuste se necessário)
from extraction_pipeline.config import (
    ATTACHMENTS_DIR,
    FILTERS_DIR,
    PRECOS
)
# Importando prompts do seu projeto (ajuste se necessário)
from extraction_pipeline.prompts.prompts import (
    prompt_vitimas,
    prompt_testemunhas,
    prompt_suspeitos,
    prompt_inquerito_info,
    prompt_mapeamento
)
# Importando schemas do seu projeto (ajuste se necessário)
from extraction_pipeline.graphs.extract_data import (
    InqueritoTotal
)

# --- CONFIGURAÇÃO ---
JSON_PATH = "output/run_2025-09-29_22-56-29/sabiazinho-3.0" # Diretório com JSONs de saída para análise

# Lista de exclusão são processos cujos txt's foram avaliados e descobriu-se que ocorreram erros no parsing
EXCLUSION_FILES: List[Path] = [
    FILTERS_DIR / "outliers_bottom_1_percent.json", # Processos com poucos tokens
    FILTERS_DIR / "outliers_top_1_percent.json"     # Processos com muitos tokens
]

# Lista de inclusão são os processos que passaram pelo filtro do 'assunto' para somente homicídio e similares
INCLUSION_FILES: List[Path] = [
    FILTERS_DIR / "processes_passed_filter.json"
]

# Para simular o modo de avaliação
EVAL_MODE = False
EVAL_PATH = FILTERS_DIR / "ids_eval.json"

# --- Funções de Tokenização e Leitura ---

def get_token_count(text: str, model_name: str) -> int:
    """
    Conta os tokens de um texto usando o tokenizador apropriado
    para a família do modelo (Maritalk ou Gemini).
    """
    if model_name.startswith("gemini"):
        try:
            model = genai.GenerativeModel(model_name)
            return model.count_tokens(text).total_tokens
        except Exception as e:
            print(f"Erro ao contar tokens com Gemini para o modelo '{model_name}': {e}")
            return 0
    elif "sabia" in model_name:
        return maritalk_count_tokens(text, model_name)
    else:
        raise ValueError(f"Modelo '{model_name}' não suportado para contagem de tokens.")

def load_ids_from_json_files(file_paths: List[Path]) -> Set[str]:
    """
    Carrega IDs de arquivos JSON, lidando com múltiplos formatos.
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

            if isinstance(data, dict):
                all_ids.update(map(str, data.keys()))
            elif isinstance(data, list):
                if not data:
                    continue
                if isinstance(data[0], dict):
                    for item in data:
                        if isinstance(item, dict) and "NumMP" in item and item["NumMP"] is not None:
                            all_ids.add(str(item["NumMP"]))
                else:
                    all_ids.update(map(str, data))
            else:
                print(f"Aviso: Formato JSON não suportado em '{file_path.name}'.")

        except json.JSONDecodeError:
            print(f"Erro: Falha ao decodificar JSON do arquivo '{file_path}'.")
        except Exception as e:
            print(f"Erro ao ler o arquivo '{file_path}': {e}")
            
    return all_ids

def extrair_texto_do_json(data: dict) -> str:
    """
    Converte o objeto JSON inteiro em uma string formatada.
    """
    return json.dumps(data, ensure_ascii=False, indent=2)

# --- Funções de Análise ---

def analisar_media_tokens_json(model_name: str, json_dir: Path = Path(JSON_PATH)):
    """
    Analisa um diretório com arquivos JSON de saída e calcula a média de tokens.
    """
    print(f"\nCalculando tokens de SAÍDA (dos JSONs gerados) para o modelo: {model_name}...")
    if not json_dir.is_dir():
        print(f"Erro: O diretório de JSONs '{json_dir}' não foi encontrado.")
        return None

    glob_pattern = "*/*/*.json"
    json_files = list(json_dir.glob(glob_pattern))
    
    if not json_files:
        print(f"Nenhum arquivo .json encontrado na estrutura '{glob_pattern}' dentro de '{json_dir}'.")
        return None

    total_tokens = 0
    arquivos_processados = 0
    
    for file_path in json_files:
        try:
            with file_path.open('r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            texto_para_tokenizar = extrair_texto_do_json(json_data)
            
            if texto_para_tokenizar:
                total_tokens += get_token_count(texto_para_tokenizar, model_name)
                arquivos_processados += 1
        except Exception as e:
            print(f"Erro ao processar o arquivo JSON de saída {file_path}: {e}")

    if arquivos_processados > 0:
        media_tokens = total_tokens / arquivos_processados
        print(f"  - Média de Tokens por Arquivo JSON de Saída: {media_tokens:,.0f}")
        return media_tokens
    else:
        print("Nenhum arquivo JSON de saída válido foi processado.")
        return None

def perform_dataset_file_analysis():
    """
    Executa a análise de arquivos, contagens e filtros do dataset, apresentando
    a lógica como um funil de seleção.
    Retorna os IDs dos processos a serem executados, um mapa de ID para path e a contagem.
    """
    print("--- Análise e Seleção do Conjunto de Dados para o Pipeline ---")

    # --- ETAPA 0: LEVANTAMENTO INICIAL ---
    # Verifica se o diretório principal existe
    if not ATTACHMENTS_DIR.is_dir():
        print(f"\n[ERRO] O diretório de anexos '{ATTACHMENTS_DIR}' não foi encontrado.")
        return None, None, 0

    # Carrega os critérios de filtragem
    inclusion_ids = load_ids_from_json_files([EVAL_PATH] if EVAL_MODE and EVAL_PATH.exists() else INCLUSION_FILES)
    exclusion_ids = load_ids_from_json_files(EXCLUSION_FILES)

    # Mapeia todos os processos existentes em disco que tiveram parsing bem-sucedido (possuem .txt)
    all_process_paths = [path for path in ATTACHMENTS_DIR.glob("*/*") if path.is_dir()]
    id_to_path = {p.name: p for p in all_process_paths}
    process_ids_with_txt = {p.name for p in all_process_paths if any(p.glob('*.txt'))}

    # --- FUNIL DE SELEÇÃO DE DOCUMENTOS ---
    print("\n--- Funil de Seleção de Documentos ---")

    # 1. Ponto de Partida: Total de processos de interesse
    print(f"\n[PASSO 1] Ponto de Partida: Assuntos de Interesse")
    print(f"  - Total de processos de interesse (ex: 'homicídio') definidos nos arquivos de filtro: {len(inclusion_ids):,}")

    # 2. Filtro de Disponibilidade: Documentos que existem e foram parseados
    candidates_with_txt = inclusion_ids.intersection(process_ids_with_txt)
    lost_at_step_2 = len(inclusion_ids) - len(candidates_with_txt)
    print(f"\n[PASSO 2] Filtro de Disponibilidade: Documentos encontrados e com parsing bem-sucedido")
    print(f"  - Destes, {len(candidates_with_txt):,} foram encontrados em disco E tiveram o parsing inicial bem-sucedido (possuem pasta e .txt).")
    print(f"  └─ Descarte: {lost_at_step_2:,} processos foram descartados (não encontrados ou falha no parsing).")

    # 3. Filtro de Qualidade: Exclusão de outliers
    outliers_found = candidates_with_txt.intersection(exclusion_ids)
    final_runnable_with_txt_ids = candidates_with_txt.difference(exclusion_ids)
    print(f"\n[PASSO 3] Filtro de Qualidade: Exclusão de outliers de tokens")
    print(f"  - Deste grupo, {len(outliers_found):,} processos foram removidos por estarem na lista de exclusão (outliers).")
    
    # 4. Resultado Final
    final_runnable_with_txt_count = len(final_runnable_with_txt_ids)
    print("\n------------------------------------------------------------------")
    print(f"  Resultado Final: {final_runnable_with_txt_count:,} processos estão aptos para a execução.")
    print("------------------------------------------------------------------")


    # --- SUMÁRIO EXECUTIVO ---
    # O box de resultado e os insights acionáveis continuam úteis
    print("\n--- Sumário Executivo ---")
    print("\n+------------------------------------------------------+")
    print(f"| NÚMERO FINAL DE PROCESSOS A SEREM EXECUTADOS: {final_runnable_with_txt_count:<5} |")
    print("+------------------------------------------------------+")
    
    # Insights acionáveis calculados de forma mais direta agora
    total_on_disk = len(id_to_path)
    total_with_txt = len(process_ids_with_txt)
    parsing_failures_total = total_on_disk - total_with_txt
    
    print("\n[!] INSIGHTS ACIONÁVEIS:")
    print(f"1. FALHA GERAL DE PARSING: De {total_on_disk:,} processos baixados, {parsing_failures_total:,} falharam no parsing inicial (não geraram .txt).")
    print(f"2. DADOS DE INTERESSE PERDIDOS: {lost_at_step_2:,} processos de interesse não puderam ser processados por indisponibilidade ou falha de parsing.")
    print(f"3. QUALIDADE DE DADOS: {len(outliers_found):,} processos de interesse foram ativamente ignorados por problemas de qualidade (outliers).")
    
    print("\n--- Análise de Arquivos Concluída ---")
    
    return final_runnable_with_txt_ids, id_to_path, final_runnable_with_txt_count

def calculate_tokens_for_model(model_name: str, runnable_ids: Set[str], id_to_path: dict, file_count: int):
    """
    Calcula tokens de entrada para o modelo.
    - Para Sabia/Sabiazinho: conta todos.
    - Para Gemini: conta até 1000 processos via API e extrapola.
    """
    if file_count == 0:
        return 0, 0

    ids_to_process = list(runnable_ids)

    # --- Caso Gemini (lento) ---
    if model_name.startswith("gemini"):
        SAMPLE_LIMIT = 1000
        sample_ids = ids_to_process[:min(SAMPLE_LIMIT, file_count)]
        print(f"\n[Gemini] Contando tokens em {len(sample_ids)} processos e extrapolando para {file_count}...")

        total_tokens_sample = 0
        for process_id in sample_ids:
            proc_path = id_to_path[process_id]
            txt_file = next(proc_path.glob("*.txt"), None)
            if txt_file:
                try:
                    content = txt_file.read_text(encoding="utf-8", errors="ignore")
                    total_tokens_sample += get_token_count(content, model_name)
                except Exception as e:
                    print(f"Aviso: não foi possível contar tokens de {txt_file}. Erro: {e}")

        if not sample_ids:
            return 0, 0

        avg_tokens_per_doc = total_tokens_sample / len(sample_ids)
        total_tokens = avg_tokens_per_doc * file_count

        # Calcula prompts + schema (fixo por processo)
        prompt_tokens = (
            get_token_count(prompt_vitimas, model_name)
            + get_token_count(prompt_inquerito_info, model_name)
            + get_token_count(prompt_suspeitos, model_name)
            + get_token_count(prompt_testemunhas, model_name)
            + get_token_count(prompt_mapeamento, model_name)
        )
        schemas_tokens = get_token_count(
            json.dumps(InqueritoTotal.model_json_schema(), indent=2, ensure_ascii=False), model_name
        )

        num_prompts = 5
        total_tokens_in = num_prompts * total_tokens + file_count * (prompt_tokens + schemas_tokens)
        avg_tokens = avg_tokens_per_doc

    # --- Caso Sabia/Sabiazinho (rápido) ---
    else:
        print(f"\n[{model_name}] Contando tokens em todos os {file_count} processos...")
        total_tokens = 0
        for process_id in ids_to_process:
            proc_path = id_to_path[process_id]
            txt_file = next(proc_path.glob("*.txt"), None)
            if txt_file:
                try:
                    content = txt_file.read_text(encoding="utf-8", errors="ignore")
                    total_tokens += get_token_count(content, model_name)
                except Exception as e:
                    print(f"Aviso: não foi possível contar tokens de {txt_file}. Erro: {e}")

        prompt_tokens = (
            get_token_count(prompt_vitimas, model_name)
            + get_token_count(prompt_inquerito_info, model_name)
            + get_token_count(prompt_suspeitos, model_name)
            + get_token_count(prompt_testemunhas, model_name)
            + get_token_count(prompt_mapeamento, model_name)
        )
        schemas_tokens = get_token_count(
            json.dumps(InqueritoTotal.model_json_schema(), indent=2, ensure_ascii=False), model_name
        )

        num_prompts = 5
        total_tokens_in = num_prompts * total_tokens + file_count * (prompt_tokens + schemas_tokens)
        avg_tokens = total_tokens / file_count if file_count else 0

    print(f"  - Média de Tokens por Documento: {avg_tokens:,.0f}")
    print(f"  - Total de Tokens (Entrada + Prompts + Schemas): {total_tokens_in:,.0f}")

    return total_tokens_in, file_count

# --- Bloco de Execução Principal ---

if __name__ == '__main__':
    load_dotenv()
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

    # Executa a análise de arquivos UMA VEZ (reporta o total)
    runnable_ids, id_to_path, num_files = perform_dataset_file_analysis()

    if num_files == 0 or not runnable_ids:
        print("\nNenhum arquivo para processar. Encerrando o script de cálculo de custos.")
        exit()

    # Itera sobre os modelos para calcular tokens e custos (pode usar o limite interno)
    models_to_analyze = ["sabiazinho-3.0", "sabia-3.0", "gemini-2.5-flash", "gemini-2.5-pro"]
    results = {}

    for model in models_to_analyze:
        print(f"\n{'='*20} ANALISANDO CUSTOS PARA O MODELO: {model.upper()} {'='*20}")
        try:
            total_tokens_in, processed_files_count = calculate_tokens_for_model(model, runnable_ids, id_to_path, num_files)
            
            media_tokens_out = analisar_media_tokens_json(model_name=model)
            
            if media_tokens_out is not None:
                results[model] = {
                    "tokens_in": total_tokens_in,
                    # USA A CONTAGEM DE ARQUIVOS REALMENTE PROCESSADOS
                    "tokens_out": media_tokens_out * processed_files_count 
                }
            else:
                print(f"Não foi possível calcular os tokens de saída para o modelo {model}.")
                results[model] = None

        except ValueError as e:
            print(f"Erro ao analisar o modelo {model}: {e}")
        except Exception as e:
            print(f"Ocorreu um erro inesperado ao processar o modelo {model}: {e}")

    # 3. Imprime o relatório de custos comparativo final (sem alterações aqui)
    print(f"\n\n{'='*25} RELATÓRIO DE CUSTOS COMPARATIVO {'='*25}")
    
    for model, data in results.items():
        if data is None:
            print(f"\n--- {model.upper()} ---")
            print("Cálculo de custo não disponível.")
            continue
        # ... (o resto desta seção permanece igual)
        tokens_in = data["tokens_in"]
        tokens_out = data["tokens_out"]
        
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
        
    print(f"\n{'='*75}")