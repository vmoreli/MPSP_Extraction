import os
import json
from typing import List, Optional, Set

from pipeline.config import (
    ATTACHMENTS_DIR,
    FILTERS_DIR
)

# Extrair numMP dos jsons de inclusão/exclusão, lida de forma inteligente com formatos diferentes
def _load_json_set(file_path: Optional[str]) -> Set[str]:
    """
    Carrega um arquivo JSON e extrai um conjunto de números de processo (NumMP),
    independentemente da estrutura do JSON (dicionário, lista de objetos, ou lista simples).
    """
    if not file_path or not os.path.exists(file_path):
        return set()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # --- Lógica de extração inteligente ---

        # Caso 1: O JSON é um dicionário. As chaves são os números.
        # Ex: { "1301...": 4198910, ... }
        if isinstance(data, dict):
            # As chaves já são strings, o que é perfeito.
            return set(data.keys())

        # Caso 2: O JSON é uma lista.
        elif isinstance(data, list):
            if not data:  # Se a lista estiver vazia
                return set()

            # Verificamos o tipo do primeiro item para decidir como processar
            first_item = data[0]

            # Caso 2a: Lista de objetos (dicionários).
            # Ex: [ { "NumMP": 1300..., "Assunto": "..." }, ... ]
            if isinstance(first_item, dict) and "NumMP" in first_item:
                numbers = set()
                for item in data:
                    # Verificação de segurança para cada item da lista
                    if isinstance(item, dict):
                        num_mp = item.get("NumMP")
                        if num_mp is not None:
                            # Convertemos para string para corresponder aos nomes das pastas
                            numbers.add(str(num_mp))
                return numbers
            
            # Caso 2b: Lista simples de números ou strings.
            # Ex: [ "1301...", 1307... ]
            else:
                # Convertemos todos os itens para string
                return {str(item) for item in data}

        # Se não for nem dicionário nem lista, retorna um conjunto vazio com um aviso.
        else:
            print(f"Warning: Unexpected JSON structure in {file_path}. Expected a dict or a list.")
            return set()

    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not read or parse JSON file {file_path}. Error: {e}")
        return set()

def load_process_paths(
    attachments_dir: str,
    exclusion_files: Optional[List[str]],
    inclusion_files: Optional[List[str]],
    eval_mode: bool = False,
    eval_file_path: Optional[str] = None
) -> List[str]:
    """
    Varre o diretório de anexos para encontrar caminhos de processos válidos.

    Em modo padrão (eval_mode=False), aplica a lógica de filtro e exclusão.
    Em modo de avaliação (eval_mode=True), carrega a lista de processos
    exclusivamente do arquivo especificado em `eval_file_path`.

    Args:
        attachments_dir: O diretório raiz dos anexos.
        exclusion_files: Lista de arquivos JSON com processos a serem excluídos.
        inclusion_files: Lista de arquivos JSON com processos a serem incluídos.
        eval_mode: Se True, ativa o modo de avaliação.
        eval_file_path: Caminho para o arquivo JSON contendo os IDs dos processos
                        a serem usados no modo de avaliação.
    
    Returns:
        Uma lista de caminhos completos para os processos a serem analisados.
    
    Raises:
        ValueError: Se `eval_mode` for True mas `eval_file_path` não for fornecido.
        FileNotFoundError: Se o `attachments_dir` não for encontrado.
    """
    # --- Mapear todos os processos existentes no disco ---
    # Esta etapa é necessária para ambos os modos, para converter números em caminhos.
    if not os.path.isdir(attachments_dir):
        raise FileNotFoundError(f"Attachments directory not found: {attachments_dir}")

    all_process_paths = []
    for seven_digit_dir in os.listdir(attachments_dir):
        seven_digit_path = os.path.join(attachments_dir, seven_digit_dir)
        if os.path.isdir(seven_digit_path):
            for process_dir in os.listdir(seven_digit_path):
                process_path = os.path.join(seven_digit_path, process_dir)
                if os.path.isdir(process_path):
                    all_process_paths.append(process_path)
    
    process_path_map = {os.path.basename(p): p for p in all_process_paths}
    
    final_process_numbers = set()

    # --- Definir a lista de processos com base no modo ---
    if eval_mode:
        # --- MODO DE AVALIAÇÃO ---
        print("--- Running in EVALUATION mode ---")
        if not eval_file_path:
            raise ValueError("Evaluation mode is enabled, but 'eval_file_path' was not provided.")
        
        print(f"Loading process list exclusively from: {eval_file_path}")
        final_process_numbers = _load_json_set(eval_file_path)

    else:
        # --- MODO PADRÃO (com filtros de inclusão/exclusão) ---
        print("--- Running in STANDARD mode ---")
        all_discovered_processes = set(process_path_map.keys())

        processes_to_exclude = set()
        if exclusion_files:
            print(f"Loading {len(exclusion_files)} exclusion file(s)...")
            for file_path in exclusion_files:
                processes_to_exclude.update(_load_json_set(file_path))

        processes_to_include = set()
        if inclusion_files:
            print(f"Loading {len(inclusion_files)} inclusion file(s)...")
            for file_path in inclusion_files:
                processes_to_include.update(_load_json_set(file_path))
        
        if processes_to_include:
            print(f"Base list aggregated to {len(processes_to_include)} processes.")
            final_process_numbers = processes_to_include - processes_to_exclude
        else:
            print(f"Scanning all {len(all_discovered_processes)} processes found on disk.")
            final_process_numbers = all_discovered_processes - processes_to_exclude

    # --- Converter os números de processo finais em caminhos ---
    # Ordena para garantir que a ordem de processamento seja sempre a mesma
    sorted_final_numbers = sorted(list(final_process_numbers))

    final_paths = [
        process_path_map[num] 
        for num in sorted_final_numbers 
        if num in process_path_map
    ]
    
    # Avisa sobre processos listados nos JSONs mas não encontrados em disco.
    non_existent_processes = final_process_numbers - set(process_path_map.keys())
    if non_existent_processes:
        print(f"Warning: {len(non_existent_processes)} processes from JSON lists were not found on disk and will be ignored.")

    print(f"Found {len(final_paths)} processes to analyze after applying all filters.")
    return final_paths