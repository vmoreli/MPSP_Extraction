import os
import json
import glob
import random
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel
# Importa a biblioteca para paralelismo
from concurrent.futures import ProcessPoolExecutor, as_completed
import time # Para medir o tempo de execução

# Importando paths
from extraction_pipeline.config import (
    OUTPUT_DIR,
    ATTACHMENTS_DIR,
    MODEL,
    FILTERS_DIR,
    MAX_PROCESSES
)

# Importando os outros módulos
from extraction_pipeline.services.loader_service import load_process_paths

# Importando pipeline
from extraction_pipeline.graphs.extract_data import pipeline

# Função que processa um único caminho de processo
def process_single_path(process_path: str, unique_run_output_dir: Path, model: str) -> str:
    """
    Processa um único diretório de processo: lê o texto, invoca o pipeline e salva o resultado.
    Retorna uma mensagem de status.
    """
    process_number = os.path.basename(process_path)
    seven_digit_prefix = os.path.basename(os.path.dirname(process_path))

    try:
        # Encontra todos os arquivos .txt no diretório do processo
        txt_files = glob.glob(os.path.join(process_path, "*.txt"))

        if not txt_files:
            return f"WARNING: No .txt files found in {process_path}. Skipping."

        process_text = ""
        # Ordena os arquivos para garantir uma concatenação consistente
        for txt_file_path in sorted(txt_files):
            with open(txt_file_path, 'r', encoding='utf-8') as f:
                process_text += f.read() + "\n"

        # Chama o grafo para realizar a extração
        extraction_result = pipeline.invoke({
            "document": process_text
        })

        serializable_result = {}
        for key, value in extraction_result.items():
            if isinstance(value, BaseModel):
                serializable_result[key] = value.model_dump()
            else:
                serializable_result[key] = value

        # Construir o caminho de saída dinamicamente
        output_path = (
            unique_run_output_dir / model / seven_digit_prefix / process_number
        )
        output_path.mkdir(parents=True, exist_ok=True)
        output_file_path = output_path / f"{process_number}_result.json"

        # Salvar o resultado
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_result, f, ensure_ascii=False, indent=4)

        return f"SUCCESS: Successfully processed {process_number} and saved to {output_file_path}"

    except Exception as e:
        return f"ERROR: Failed to process {process_number}. Reason: {e}"

# --- Função Principal ---
def run_extraction_pipeline(
    attachments_dir: str = ATTACHMENTS_DIR,
    output_dir: str = OUTPUT_DIR,
    max_processes: Optional[int] = MAX_PROCESSES,
    model: str = MODEL,
    random_seed: Optional[int] = 42,
    exclusion_file: Optional[List[str]] = [
        FILTERS_DIR / "outliers_bottom_1_percent.json",     # outliers inferiores de num de tokens
        FILTERS_DIR / "outliers_top_1_percent.json"         # outliers superiores de num de tokens
    ],
    inclusion_file: Optional[List[str]] = [
        FILTERS_DIR / "processes_passed_filter.json"        # processos que passaram por filtro no assunto (homicídio e relacionados)
    ],
    eval_mode: bool = False,                                # True se for fazer eval
    eval_path: Optional[str] = None                         # Se for fazer eval, passa um caminho com os ids dos processos que serão utiizados
) -> None:
    """
    Executa o pipeline de extração de dados de forma paralela.
    """
    print("--- Starting Parallel Extraction Pipeline ---")
    start_time = time.time()

    # --- Gerar um timestamp único para esta execução ---
    run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    unique_run_output_dir = Path(output_dir) / f"run_{run_timestamp}"

    # Carregar e filtrar os caminhos dos processos
    process_paths = load_process_paths(attachments_dir, exclusion_file, inclusion_file, eval_mode, eval_path)

    # Embaralhar a lista pela seed (aleatório determinístico)
    if random_seed is not None:
        print(f"Shuffling process list with random seed: {random_seed}")
        random.seed(random_seed)
        random.shuffle(process_paths)

    # Limitar o número de processos, se especificado
    if max_processes is not None:
        print(f"Limiting to a maximum of {max_processes} total processes.")
        process_paths = process_paths[:max_processes]
    
    total_to_process = len(process_paths)
    print(f"\n--- Starting processing of {total_to_process} files using parallel workers ---")

    # --- Usar ProcessPoolExecutor para paralelizar a execução ---
    num_workers = os.cpu_count()
    print(f"Using {num_workers} parallel workers.")

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        # Submete todas as tarefas ao pool. `future` é um objeto que representa a execução.
        futures = {
            executor.submit(process_single_path, path, unique_run_output_dir, model): path
            for path in process_paths
        }

        # Processa os resultados à medida que são concluídos
        for i, future in enumerate(as_completed(futures)):
            result_message = future.result()
            print(f"({i+1}/{total_to_process}) - {result_message}")

    end_time = time.time()
    print("\n--- Extraction Pipeline Finished ---")
    print(f"Total execution time: {end_time - start_time:.2f} seconds")


if __name__ == '__main__':
    run_extraction_pipeline(
        eval_mode=True,
        eval_path="ids_eval.json",
        max_processes=5
    )