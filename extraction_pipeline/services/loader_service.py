import os
import json
from typing import List, Optional, Set

from extraction_pipeline.config import (
    ATTACHMENTS_DIR,
    FILTERS_DIR
)


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
    exclusion_files: Optional[List[str]], # Nome da variável no plural para clareza
    filtered_processes_json_paths: Optional[List[str]] # Nome da variável no plural para clareza
) -> List[str]:
    """
    Varre o diretório de anexos para encontrar todos os caminhos de processos válidos
    e aplica a lógica de filtro e exclusão a partir de múltiplas listas.
    """
    # --- ETAPA 1: Encontrar todos os processos existentes no disco (inalterado) ---
    all_process_paths = []
    if not os.path.isdir(attachments_dir):
        raise FileNotFoundError(f"Attachments directory not found: {attachments_dir}")

    for seven_digit_dir in os.listdir(attachments_dir):
        seven_digit_path = os.path.join(attachments_dir, seven_digit_dir)
        if os.path.isdir(seven_digit_path):
            for process_dir in os.listdir(seven_digit_path):
                process_path = os.path.join(seven_digit_path, process_dir)
                if os.path.isdir(process_path):
                    all_process_paths.append(process_path)
    
    process_path_map = {os.path.basename(p): p for p in all_process_paths}
    all_discovered_processes = set(process_path_map.keys())

    # --- ETAPA 2: Carregar e AGREGAR as listas de inclusão e exclusão ---
    processes_to_exclude = set()
    if exclusion_files:
        print(f"Loading {len(exclusion_files)} exclusion file(s)...")
        for file_path in exclusion_files:
            # O método .update() adiciona todos os itens de um set em outro
            processes_to_exclude.update(_load_json_set(file_path))

    processes_to_include = set()
    if filtered_processes_json_paths:
        print(f"Loading {len(filtered_processes_json_paths)} inclusion file(s)...")
        for file_path in filtered_processes_json_paths:
            processes_to_include.update(_load_json_set(file_path))
    
    # --- ETAPA 3 e 4: Lógica de filtro e conversão para caminhos ---
    final_process_numbers = set()

    if processes_to_include:
        print(f"Base list aggregated to {len(processes_to_include)} processes.")
        final_process_numbers = processes_to_include - processes_to_exclude
    else:
        print(f"Scanning all {len(all_discovered_processes)} processes found on disk.")
        final_process_numbers = all_discovered_processes - processes_to_exclude

    # Para que ordem dos processos seja determinística
    sorted_final_numbers = sorted(list(final_process_numbers))

    final_paths = [
        process_path_map[num] 
        for num in sorted_final_numbers 
        if num in process_path_map
    ]
    
    non_existent_processes = final_process_numbers - set(process_path_map.keys())
    if non_existent_processes:
        print(f"Warning: {len(non_existent_processes)} processes from JSON lists were not found on disk and will be ignored.")

    print(f"Found {len(final_paths)} processes to analyze after applying all filters.")
    return final_paths