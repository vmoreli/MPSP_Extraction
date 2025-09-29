import os
import json
import random
import argparse
from pathlib import Path
from typing import Optional, List

# Importando paths
from extraction_pipeline.config import (
    OUTPUT_DIR,
    ATTACHMENTS_DIR,
    MODEL,
    FILTERS_DIR
)

# Importando os outros módulos
from extraction_pipeline.services.loader_service import load_process_paths

# --- Main Extraction Pipeline Function ---
def run_extraction_pipeline(
    attachments_dir: str = ATTACHMENTS_DIR,
    output_dir: str = OUTPUT_DIR,
    max_processes: Optional[int] = None,
    model: str = MODEL,
    random_seed: Optional[int] = 42,
    exclusion_file: Optional[List[str]] = [
        FILTERS_DIR / "outliers_bottom_1_percent.json",     # Outliers inferiores (em termos de números de tokens)
        FILTERS_DIR / "outliers_top_1_percent.json"         # Outliers superiores (em termos de números de tokens)
    ],
    inclusion_file: Optional[List[str]] = [
        FILTERS_DIR / "processes_passed_filter.json"        # Processos que passaram pelos filtros de assunto (relacionados a homicídios)
    ]
) -> None:
    """
    Executa o pipeline de extração de dados varrendo subdiretórios
    em ATTACHMENTS_DIR, onde há uma pasta para os 7 primeiros dígitos
    e dentro dela, pastas para cada processo.
    Salva os resultados de cada processo em um arquivo JSON separado,
    seguindo a organização de diretórios:
    output_dir/nome_do_modelo/7_primeiros_digitos/numero_processo/estrategia/jsons

    A ordem de varredura dos diretórios de processo pode ser aleatória e determinística
    se uma `random_seed` for fornecida. Processos listados em `exclusion_file` serão pulados.
    Pode opcionalmente usar uma lista pré-filtrada de processos via `filtered_processes_json_path`.

    Args:
        attachments_dir: O diretório raiz que contém as pastas de 7 dígitos.
        output_dir: Diretório onde os resultados JSON serão salvos.
        max_processes: Limite o número de processos (pastas de processo aninhadas)
                       a serem analisados. Se None, todos serão analisados.
        model: O nome do modelo usado para a extração, que será usado para criar uma pasta de saída.
        random_seed: Uma semente inteira para o gerador de números aleatórios. Se fornecida,
                     a ordem de processamento será aleatória, mas determinística.
                     Se None, a ordem de varredura será a padrão do os.walk (determinística).
        exclusion_file: Caminho para um arquivo JSON contendo os números de processo a serem excluídos.
        filtered_processes_json_path: Caminho para um arquivo JSON (gerado pelo script de filtro)
                                      contendo la lista de processos a serem extraídos.
                                      Se fornecido, o pipeline processará APENAS esses processos.
    """
    print("--- Starting Extraction Pipeline ---")

    # 1. Carregar e filtrar os caminhos dos processos usando o serviço de loader
    process_paths = load_process_paths(attachments_dir, exclusion_file, inclusion_file)

    # 2. Embaralhar a lista se uma seed foi fornecida
    if random_seed is not None:
        print(f"Shuffling process list with random seed: {random_seed}")
        random.seed(random_seed)
        random.shuffle(process_paths)

    # 3. Limitar o número de processos, se especificado
    if max_processes is not None:
        print(f"Limiting to a maximum of {max_processes} processes.")
        process_paths = process_paths[:max_processes]

    # 4. Iterar sobre cada processo e executar a extração
    total_to_process = len(process_paths)
    print(f"\n--- Processing {total_to_process} files ---")

    for i, process_path in enumerate(process_paths):
        process_number = os.path.basename(process_path)
        seven_digit_prefix = os.path.basename(os.path.dirname(process_path))
        
        print(f"\n({i+1}/{total_to_process}) Processing: {process_number}")

        try:
            # Assumindo que o texto do processo está em um arquivo chamado 'process_text.txt'
            # Adapte este nome de arquivo se necessário
            input_txt_path = os.path.join(process_path, 'process_text.txt')
            
            if not os.path.exists(input_txt_path):
                print(f"  Warning: 'process_text.txt' not found in {process_path}. Skipping.")
                continue

            with open(input_txt_path, 'r', encoding='utf-8') as f:
                process_text_content = f.read()

            # CHAMAR GRAFO AQUI
            
            # Construir o caminho de saída dinamicamente
            output_path = (
                Path(output_dir) / model / seven_digit_prefix / process_number /
                "jsons"
            )
            
            # Criar diretórios de saída se não existirem
            output_path.mkdir(parents=True, exist_ok=True)
            
            output_file_path = output_path / f"{process_number}_result.json"
            
            # Salvar o resultado
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(extraction_result, f, ensure_ascii=False, indent=4)
            
            print(f"  Successfully saved result to: {output_file_path}")

        except Exception as e:
            print(f"  ERROR: Failed to process {process_number}. Reason: {e}")

    print("\n--- Extraction Pipeline Finished ---")


if __name__ == '__main__':
    run_extraction_pipeline()