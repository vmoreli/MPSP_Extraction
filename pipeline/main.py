import os
import json
import glob
import random
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

from pipeline.config import (
    OUTPUT_DIR,
    ATTACHMENTS_DIR,
    MODEL,
    FILTERS_DIR,
    MAX_PROCESSES,
)

from pipeline.services.loader_service import load_process_paths
from pipeline.graphs.extract_data import pipeline


def process_single_path(process_path: str, model: str):
    """
    Processa um único diretório de processo: lê o texto, invoca o pipeline e retorna (process_number, resultado).
    """
    process_number = os.path.basename(process_path)
    try:
        txt_files = glob.glob(os.path.join(process_path, "*.txt"))
        if not txt_files:
            return process_number, {"status": "warning", "message": f"No .txt files found in {process_path}"}

        process_text = ""
        for txt_file_path in sorted(txt_files):
            with open(txt_file_path, 'r', encoding='utf-8') as f:
                process_text += f.read() + "\n"

        extraction_result = pipeline.invoke({"document": process_text})

        serializable_result = {}
        for key, value in extraction_result.items():
            if isinstance(value, BaseModel):
                serializable_result[key] = value.model_dump()
            else:
                serializable_result[key] = value

        return process_number, {"status": "success", "result": serializable_result}

    except Exception as e:
        return process_number, {"status": "error", "message": str(e)}


def run_extraction_pipeline(
    attachments_dir: str = ATTACHMENTS_DIR,
    output_dir: str = OUTPUT_DIR,
    max_processes: Optional[int] = MAX_PROCESSES,
    model: str = MODEL,
    random_seed: Optional[int] = 42,
    exclusion_file: Optional[List[str]] = [
        FILTERS_DIR / "outliers_bottom_1_percent.json",
        FILTERS_DIR / "outliers_top_1_percent.json"
    ],
    inclusion_file: Optional[List[str]] = [
        FILTERS_DIR / "processes_passed_filter.json"
    ],
    eval_mode: bool = False,
    eval_path: Optional[str] = None
) -> None:
    """
    Executa o pipeline de extração de dados e salva tudo em um único JSON.
    """
    print("--- Starting Parallel Extraction Pipeline ---")
    start_time = time.time()

    run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    unique_run_output_dir = Path(output_dir) / f"run_{run_timestamp}"
    unique_run_output_dir.mkdir(parents=True, exist_ok=True)

    consolidated_output_path = unique_run_output_dir / f"results_{model}.json"

    process_paths = load_process_paths(attachments_dir, exclusion_file, inclusion_file, eval_mode, eval_path)

    if random_seed is not None:
        random.seed(random_seed)
        random.shuffle(process_paths)

    if max_processes is not None:
        process_paths = process_paths[:max_processes]

    total_to_process = len(process_paths)
    print(f"\n--- Processing {total_to_process} files in parallel ---")

    num_workers = os.cpu_count()
    print(f"Using {num_workers} parallel workers.\n")

    results_dict = {}

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(process_single_path, path, model): path for path in process_paths}

        for i, future in enumerate(as_completed(futures)):
            process_number, result = future.result()
            results_dict[process_number] = result
            print(f"({i+1}/{total_to_process}) - {process_number}: {result.get('status', 'unknown')}")

    with open(consolidated_output_path, 'w', encoding='utf-8') as f:
        json.dump(results_dict, f, ensure_ascii=False, indent=4)

    end_time = time.time()
    print("\n--- Extraction Pipeline Finished ---")
    print(f"Results saved to: {consolidated_output_path}")
    print(f"Total execution time: {end_time - start_time:.2f} seconds")


if __name__ == '__main__':
    run_extraction_pipeline(
        eval_mode=True,
        eval_path="data/ids_eval.json",
    )
