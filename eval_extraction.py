import json
from pathlib import Path
from difflib import SequenceMatcher
from typing import Any, Dict, List, Tuple, Union
from enum import Enum
# ============================================================
# LLM
# ============================================================

from extraction_pipeline.services.llm_services import call_llm
from extraction_pipeline.prompts.prompts import prompt_compare_str
from extraction_pipeline.schemas.eval_schemas import Equal

# ============================================================
# EMBEDDINGS
# ============================================================

from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Config flags
STR_COMPARE_EMB = False                  # Ativa embeddings ou não
sentence_model= None

def get_sentence_model():
    """Carrega o modelo globalmente"""
    global sentence_model
    if sentence_model is None:
        sentence_model = SentenceTransformer("intfloat/multilingual-e5-large")
    return sentence_model


def cosine_sim(vec1, vec2):
    """Retorna similaridade coseno"""
    return float(cosine_similarity([vec1], [vec2])[0][0])


def sentence_embedding(text: str) -> np.ndarray:
    """Retorna embedding da frase inteira com modelo pretreinado (multilingual-e5-large)."""
    model = get_sentence_model()
    return model.encode(text or "", convert_to_numpy=True)


# ============================================================
# CONFIGURAÇÃO DE ENTRADA
# ============================================================

GROUNDTRUTH_PATH = Path("")
PREDICOES_PATH = Path("")
OUTPUT_PATH = Path("")

# ============================================================
# LLM como juiz
# ============================================================

def compare_strings_llm_as_a_judge(gt_str, value_str):
    prompt = prompt_compare_str.format(
        gt_str=gt_str,
        value_str=value_str
    )

    response_content = call_llm(
        prompt=prompt,
        output_schema=Equal
    )
    return response_content.equal

# ============================================================
# Funções utilitárias de similaridade e comparação
# ============================================================
    

def compare_strings_similarity(gt_str: str, value_str: str):
    if STR_COMPARE_EMB: # Comparação com embeddings
        emb_gt = sentence_embedding(gt_str)
        emb_pred = sentence_embedding(value_str)
        return cosine_sim(emb_gt, emb_pred)
    else:
        eq = compare_strings_llm_as_a_judge(gt_str, value_str)
        return eq

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
        matches = [
            max(compare_strings_similarity(x, y) for y in pred_list)
            for x in gt_list
        ]

        # Se qualquer uma das comparações não for igual (False ou abaixo do limiar)
        all_equal = all(match for match in matches)
        avg_sim = sum(float(match) for match in matches) / len(matches)

        return all_equal, avg_sim


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