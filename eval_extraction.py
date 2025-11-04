import json
from pathlib import Path
from difflib import SequenceMatcher
from typing import Any, Dict, List, Tuple, Union
from enum import Enum

# ============================================================
# CONFIGURAÇÃO DE ENTRADA
# ============================================================

GROUNDTRUTH_PATH = Path("")
PREDICOES_PATH = Path("")
OUTPUT_PATH = Path("")

STR_COMPARE_EMB = False

# ============================================================
# Funções utilitárias de similaridade e comparação
# ============================================================

def compare_strings_similarity(gt_str: str, value_str: str):
    if STR_COMPARE_EMB: # Comparação com embeddings:
        # chama função de comparação por embeddings
        return
    else:
        # chama função de comparação por llm
        return

def compare_values(gt_value: Any, pred_value: Any) -> Tuple[bool, float]:
    """
    Compara dois valores, retornando (acerto_booleano, similaridade_float).
    Define o tipo da comparação com base no tipo do groundtruth.
    """
    # Casos triviais de None
    if gt_value is None and pred_value is None:
        return True, 1.0
    if gt_value is None or pred_value is None:
        return False, 0.0

    # Strings
    if isinstance(gt_value, str):
        sim = compare_strings_similarity(gt_value, str(pred_value))
        return sim > 0.85, sim  # threshold ajustável

    # Enums ou valores literais
    if isinstance(gt_value, Enum):
        acerto = gt_value == pred_value
        return acerto, 1.0 if acerto else 0.0

    # Booleanos
    if isinstance(gt_value, bool):
        acerto = gt_value == pred_value
        return acerto, 1.0 if acerto else 0.0

    # Números
    if isinstance(gt_value, (int, float)):
        acerto = abs(gt_value - pred_value) < 1e-6
        return acerto, 1.0 if acerto else 0.0

    # Listas
    if isinstance(gt_value, list):
        return compare_lists(gt_value, pred_value)

    # Dicionários
    if isinstance(gt_value, dict):
        return compare_dicts(gt_value, pred_value)

    # Caso não previsto
    return gt_value == pred_value, 1.0 if gt_value == pred_value else 0.0


def compare_lists(gt_list: List[Any], pred_list: List[Any]) -> Tuple[bool, float]:
    """Compara listas, considerando similaridade média entre elementos."""
    if not gt_list and not pred_list:
        return True, 1.0
    if not gt_list or not pred_list:
        return False, 0.0

    # Se lista de strings simples
    if all(isinstance(x, str) for x in gt_list):
        matches = [max(string_similarity(x, y) for y in pred_list) for x in gt_list]
        avg_sim = sum(matches) / len(matches)
        return avg_sim > 0.85, avg_sim

    # Se lista de dicionários (ex: vítimas)
    if all(isinstance(x, dict) for x in gt_list):
        sims = []
        for i, gt_item in enumerate(gt_list):
            pred_item = pred_list[i] if i < len(pred_list) else {}
            _, sim = compare_dicts(gt_item, pred_item)
            sims.append(sim)
        avg_sim = sum(sims) / len(sims)
        return avg_sim > 0.85, avg_sim

    return False, 0.0


def compare_dicts(gt_dict: Dict[str, Any], pred_dict: Dict[str, Any]) -> Tuple[bool, float]:
    """Compara dois dicionários recursivamente."""
    keys = set(gt_dict.keys()) | set(pred_dict.keys())
    sims = []
    all_correct = True
    for k in keys:
        gt_val = gt_dict.get(k)
        pred_val = pred_dict.get(k)
        correct, sim = compare_values(gt_val, pred_val)
        sims.append(sim)
        all_correct &= correct
    avg_sim = sum(sims) / len(sims) if sims else 1.0
    return all_correct, avg_sim

# ============================================================
# Avaliação geral entre groundtruth e predição
# ============================================================

def evaluate_inquerito(gt_data: Dict[str, Any], pred_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compara dois JSONs de inquéritos (GT e predição),
    retornando métricas agregadas e detalhadas.
    """
    report = {}
    total_similarities = []
    total_fields = 0

    for num_mp, gt_entry in gt_data.items():
        pred_entry = pred_data.get(num_mp)
        if pred_entry is None:
            report[num_mp] = {"status": "ausente na predição", "score": 0.0}
            continue

        correct, sim = compare_dicts(gt_entry, pred_entry)
        report[num_mp] = {
            "status": "ok" if correct else "diferenças encontradas",
            "similaridade_media": round(sim, 3)
        }
        total_similarities.append(sim)
        total_fields += 1

    media_geral = sum(total_similarities) / total_fields if total_fields > 0 else 0.0
    return {
        "media_geral": round(media_geral, 3),
        "num_processos_avaliados": total_fields,
        "detalhes": report
    }

# ============================================================
# Execução principal
# ============================================================

def main():
    with open(GROUNDTRUTH_PATH, "r", encoding="utf-8") as f:
        gt_data = json.load(f)
    with open(PREDICOES_PATH, "r", encoding="utf-8") as f:
        pred_data = json.load(f)

    resultado = evaluate_inquerito(gt_data, pred_data)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print("✅ Avaliação concluída com sucesso!")
    print(f"📊 Média geral de similaridade: {resultado['media_geral']:.3f}")
    print(f"📁 Relatório salvo em: {OUTPUT_PATH}")

# ============================================================
# Execução direta
# ============================================================

if __name__ == "__main__":
    main()
