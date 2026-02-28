import os
import json
import traceback
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Callable, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
SIMILARITY_THRESHOLD = 0.8
MODEL_NAME = "intfloat/multilingual-e5-large"

# LISTA DE CAMPOS CATEGÓRICOS (NÃO USAR EMBEDDINGS)
# A comparação deve ser exata. Se mudar uma letra que não seja normalização básica, é erro.
STRICT_FIELDS = [
    "natureza_da_autoria", 
    "classificacao_crime", 
    "resultado"
]

# ==============================================================================
# SINGLETON MODEL
# ==============================================================================
_sentence_model = None

def get_sentence_model():
    global _sentence_model
    if _sentence_model is None:
        print(f"Carregando modelo {MODEL_NAME}...")
        _sentence_model = SentenceTransformer(MODEL_NAME)
    return _sentence_model

def sentence_embedding(text: str) -> np.ndarray:
    model = get_sentence_model()
    return model.encode(text or "", convert_to_numpy=True)

def cosine_sim(vec1, vec2):
    return float(cosine_similarity([vec1], [vec2])[0][0])

# ==============================================================================
# CLASSE COLETORA DE MÉTRICAS
# ==============================================================================

class MetricsCollector:
    def __init__(self):
        self.records = []

    def log(self, process_id: str, context: str, field: str, 
            gt_val: Any, pred_val: Any, result_tag: str, score: float = 1.0):
        self.records.append({
            "process_id": process_id,
            "context": context,
            "field": field,
            "gt_value": str(gt_val) if gt_val is not None else None,
            "pred_value": str(pred_val) if pred_val is not None else None,
            "result": result_tag,
            "score": score
        })

    def get_dataframe(self):
        return pd.DataFrame(self.records)

    def print_summary(self):
        df = self.get_dataframe()
        if df.empty:
            print("Nenhum dado coletado.")
            return

        print("\n" + "="*60)
        print("RELATÓRIO DE MÉTRICAS")
        print("="*60)

        print("\n--- Distribuição de Tags de Erro/Acerto ---")
        print(df['result'].value_counts())

        ent_df = df[df['field'].str.contains("match_entidade")]
        if not ent_df.empty:
            tp = len(ent_df[ent_df['result'].isin(['ENTITY_MATCH_EXACT', 'ENTITY_MATCH_SEMANTIC'])])
            fp = len(ent_df[ent_df['result'] == 'ENTITY_EXTRA'])
            fn = len(ent_df[ent_df['result'] == 'ENTITY_MISSING'])

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

            print("\n--- Performance de Reconhecimento de Entidades (NER) ---")
            print(f"Total Matches (TP): {tp}")
            print(f"Total Extra (FP)  : {fp}")
            print(f"Total Missing (FN): {fn}")
            print(f"Precision: {precision:.2%}")
            print(f"Recall:    {recall:.2%}")
            print(f"F1-Score:  {f1:.2%}")

        field_df = df[~df['field'].str.contains("match_entidade")].copy()
        field_df['is_correct'] = field_df['result'].isin(['MATCH_EXACT', 'MATCH_SEMANTIC'])
        
        print("\n--- Acurácia por Campo (Top 10 Piores) ---")
        accuracy_per_field = field_df.groupby('field')['is_correct'].mean().sort_values()
        print(accuracy_per_field.head(10))

    def save_json_report(self, filepath="relatorio_completo.json"):
        df = self.get_dataframe()
        if df.empty: return

        report_data = {}
        report_data["global_counts"] = {k: int(v) for k, v in df['result'].value_counts().to_dict().items()}

        ent_df = df[df['field'].str.contains("match_entidade")]
        ner_metrics = {"precision": 0.0, "recall": 0.0, "f1_score": 0.0, "tp": 0, "fp": 0, "fn": 0}
        
        if not ent_df.empty:
            tp = len(ent_df[ent_df['result'].isin(['ENTITY_MATCH_EXACT', 'ENTITY_MATCH_SEMANTIC'])])
            fp = len(ent_df[ent_df['result'] == 'ENTITY_EXTRA'])
            fn = len(ent_df[ent_df['result'] == 'ENTITY_MISSING'])

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

            ner_metrics = {
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1, 4),
                "tp": int(tp), "fp": int(fp), "fn": int(fn)
            }
        
        report_data["ner_metrics"] = ner_metrics

        field_df = df[~df['field'].str.contains("match_entidade")].copy()
        field_df['is_correct'] = field_df['result'].isin(['MATCH_EXACT', 'MATCH_SEMANTIC'])
        accuracy_series = field_df.groupby('field')['is_correct'].mean()
        breakdown_df = field_df.groupby(['field', 'result']).size().unstack(fill_value=0)

        fields_list = []
        for field_name, acc in accuracy_series.sort_values(ascending=True).items():
            field_counts = breakdown_df.loc[field_name].to_dict()
            field_counts = {k: int(v) for k, v in field_counts.items() if v > 0}
            total_samples = sum(field_counts.values())

            fields_list.append({
                "field": field_name,
                "accuracy": round(float(acc), 4),
                "total_samples": total_samples,
                "breakdown": field_counts
            })

        report_data["fields_performance"] = fields_list

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=4, ensure_ascii=False)
            print(f"\nRelatório JSON salvo com sucesso em: {filepath}")
        except Exception as e:
            print(f"Erro ao salvar relatório JSON: {e}")

# ==============================================================================
# UTILITÁRIOS E LÓGICA DE VALORES
# ==============================================================================

def is_boolean_true(val: Any) -> bool:
    """
    Retorna True apenas se o valor indicar inequivocamente 'Verdadeiro'.
    """
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val != 0
    
    # Tratamento de Strings
    s = str(val).lower().strip()
    if s in ['false', 'falso', 'não', 'nao', 'n', '0', 'no']:
        return False
    return True

def treat_null_equivalents(val: Any) -> Any:
    if val is None: return None
    if isinstance(val, str):
        clean_val = val.lower().strip()
        null_synonyms = ["não informado", "nao informado", "não informada", 
                         "nao informada", "ni", "n/i", "sem informação", "ignorado"]
        if clean_val in null_synonyms: return None
        return val
    return val

def eval_value(gt: Any, pred: Any, field_name: str, context: str, 
               process_id: str, collector: MetricsCollector):
    """
    Compara valores com suporte a:
    1. Normalização de Nulos.
    2. Lógica Booleana (None == False).
    3. Bloqueio de similaridade semântica para campos estritos.
    """
    
    # 1. Normalização prévia (Trata "Não informado" como None)
    gt_treated = treat_null_equivalents(gt)
    pred_treated = treat_null_equivalents(pred)

    # 2. Lógica Booleana (Se um for bool, força comparação booleana)
    if isinstance(gt_treated, bool) or isinstance(pred_treated, bool):
        val_gt = is_boolean_true(gt_treated)
        val_pred = is_boolean_true(pred_treated)
        if val_gt == val_pred:
            collector.log(process_id, context, field_name, gt, pred, "MATCH_EXACT", 1.0)
        else:
            collector.log(process_id, context, field_name, gt, pred, "VALUE_MISMATCH", 0.0)
        return

    # 3. Match de Nulos
    if gt_treated is None and pred_treated is None:
        return 

    # 4. Erros de Nulo (Missing/Extra Field)
    if gt_treated is not None and pred_treated is None:
        collector.log(process_id, context, field_name, gt, pred, "FALSE_NEGATIVE", 0.0)
        return
    
    if gt_treated is None and pred_treated is not None:
        collector.log(process_id, context, field_name, gt, pred, "FALSE_POSITIVE", 0.0)
        return

    # 5. Match Exato (String ou Número)
    gt_norm = str(gt_treated).lower().strip() if isinstance(gt_treated, str) else gt_treated
    pred_norm = str(pred_treated).lower().strip() if isinstance(pred_treated, str) else pred_treated

    if gt_norm == pred_norm:
        collector.log(process_id, context, field_name, gt, pred, "MATCH_EXACT", 1.0)
        return

    # =========================================================================
    # BLOQUEIO DE CAMPOS ESTRITOS (NOVA LÓGICA)
    # Se o campo estiver na lista de estritos, NÃO tenta usar embeddings.
    # Se chegou até aqui, é porque o Match Exato falhou -> LOGO, É ERRO.
    # =========================================================================
    if field_name in STRICT_FIELDS:
        collector.log(process_id, context, field_name, gt, pred, "VALUE_MISMATCH", 0.0)
        return

    # 6. Strings diferentes -> Tentar Semântica (apenas para campos não-estritos)
    if isinstance(gt_treated, str) and isinstance(pred_treated, str):
        emb_gt = sentence_embedding(gt_treated)
        emb_pred = sentence_embedding(pred_treated)
        sim = cosine_sim(emb_gt, emb_pred)

        if sim >= SIMILARITY_THRESHOLD:
            collector.log(process_id, context, field_name, gt, pred, "MATCH_SEMANTIC", sim)
        else:
            collector.log(process_id, context, field_name, gt, pred, "VALUE_MISMATCH", sim)
        return

    # 7. Tipos incompatíveis (ex: int vs str)
    collector.log(process_id, context, field_name, gt, pred, "VALUE_MISMATCH", 0.0)


# ==============================================================================
# LÓGICA DE COMPARAÇÃO (LISTAS E OBJETOS)
# ==============================================================================

def eval_list_of_strings(gt_list: List[str], pred_list: List[str], 
                         field_name: str, context: str, process_id: str, 
                         collector: MetricsCollector):
    gt_list = gt_list or []
    pred_list = pred_list or []
    gt_temp = gt_list.copy()
    pred_temp = pred_list.copy()
    
    to_remove_gt = []
    to_remove_pred = []
    
    for g_item in gt_temp:
        for p_item in pred_temp:
            if g_item.lower().strip() == p_item.lower().strip():
                collector.log(process_id, context, field_name, g_item, p_item, "MATCH_EXACT", 1.0)
                to_remove_gt.append(g_item)
                to_remove_pred.append(p_item)
                break
    
    for x in to_remove_gt: gt_temp.remove(x)
    for x in to_remove_pred: pred_temp.remove(x)

    # Note: Para listas de strings genéricas, mantemos a similaridade. 
    # Se houver listas estritas no futuro, precisa adaptar aqui também.
    for i, g_item in enumerate(gt_temp):
        best_sim = -1
        best_p_idx = -1
        g_emb = sentence_embedding(g_item)
        
        for j, p_item in enumerate(pred_temp):
            if p_item is None: continue
            p_emb = sentence_embedding(p_item)
            sim = cosine_sim(g_emb, p_emb)
            if sim > best_sim:
                best_sim = sim
                best_p_idx = j
        
        if best_sim >= SIMILARITY_THRESHOLD and best_p_idx != -1:
            collector.log(process_id, context, field_name, g_item, pred_temp[best_p_idx], "MATCH_SEMANTIC", best_sim)
            pred_temp[best_p_idx] = None 
        else:
            collector.log(process_id, context, field_name, g_item, None, "VALUE_MISMATCH", best_sim if best_sim > -1 else 0)

    for p_item in pred_temp:
        if p_item is not None:
            collector.log(process_id, context, field_name, None, p_item, "EXTRA_VALUE", 0.0)


def eval_list_of_objects(gt_list: List[Dict], pred_list: List[Dict], 
                         eval_func: Callable, list_name: str, process_id: str, 
                         collector: MetricsCollector):
    gt_list = gt_list or []
    pred_list = pred_list or []

    gt_matched_indices = set()
    pred_matched_indices = set()
    pairs_to_compare = [] 

    # 1. Match Exato de Nome
    for i, gt_item in enumerate(gt_list):
        gt_name = str(gt_item.get('nome', '')).lower().strip()
        if not gt_name: continue
        for j, pred_item in enumerate(pred_list):
            if j in pred_matched_indices: continue
            pred_name = str(pred_item.get('nome', '')).lower().strip()
            if gt_name == pred_name:
                gt_matched_indices.add(i)
                pred_matched_indices.add(j)
                pairs_to_compare.append((gt_item, pred_item, "ENTITY_MATCH_EXACT"))
                break
    
    # 2. Match Semântico (sobras)
    if len(gt_matched_indices) < len(gt_list) and len(pred_matched_indices) < len(pred_list):
        for i, gt_item in enumerate(gt_list):
            if i in gt_matched_indices: continue
            gt_name = str(gt_item.get('nome', ''))
            if not gt_name: continue
            gt_emb = sentence_embedding(gt_name)
            
            best_score = -1.0
            best_idx = -1
            
            for j, pred_item in enumerate(pred_list):
                if j in pred_matched_indices: continue
                pred_name = str(pred_item.get('nome', ''))
                pred_emb = sentence_embedding(pred_name)
                sim = cosine_sim(gt_emb, pred_emb)
                if sim > best_score:
                    best_score = sim
                    best_idx = j
            
            if best_score >= SIMILARITY_THRESHOLD and best_idx != -1:
                gt_matched_indices.add(i)
                pred_matched_indices.add(best_idx)
                pairs_to_compare.append((gt_item, pred_list[best_idx], "ENTITY_MATCH_SEMANTIC"))

    # 3. Métricas
    for gt_obj, pred_obj, match_tag in pairs_to_compare:
        nome = gt_obj.get('nome')
        collector.log(process_id, list_name, "match_entidade", nome, pred_obj.get('nome'), match_tag)
        eval_func(gt_obj, pred_obj, f"{list_name}[{nome}]", process_id, collector)

    for i, gt_item in enumerate(gt_list):
        if i not in gt_matched_indices:
            nome = gt_item.get('nome', f"item_{i}")
            collector.log(process_id, list_name, "match_entidade", nome, None, "ENTITY_MISSING", 0.0)

    for j, pred_item in enumerate(pred_list):
        if j not in pred_matched_indices:
            nome = pred_item.get('nome', f"item_{j}")
            collector.log(process_id, list_name, "match_entidade", None, nome, "ENTITY_EXTRA", 0.0)

# ==============================================================================
# SCHEMAS DE AVALIAÇÃO
# ==============================================================================

def eval_pessoa_fields(gt: dict, pred: dict, context: str, pid: str, col: MetricsCollector):
    # 1. Campos Gerais
    common_fields = ['cor', 'sexo', 'profissao', 'escolaridade', 
                     'nacionalidade', 'idade', 'antecedentes_criminais']
    for f in common_fields:
        eval_value(gt.get(f), pred.get(f), f, context, pid, col)

    # 2. Status 'é_policial'
    gt_is_police_raw = gt.get('é_policial')
    pred_is_police_raw = pred.get('é_policial')
    eval_value(gt_is_police_raw, pred_is_police_raw, 'é_policial', context, pid, col)

    # 3. Campos Condicionais (Lógica de Negócio)
    police_fields = ['corporacao_policial', 'policial_em_servico']
    gt_bool = is_boolean_true(gt_is_police_raw)
    pred_bool = is_boolean_true(pred_is_police_raw)

    if not gt_bool and not pred_bool:
        pass # Ignora
    else:
        for f in police_fields:
            eval_value(gt.get(f), pred.get(f), f, context, pid, col)

def eval_vitima(gt: dict, pred: dict, context: str, pid: str, col: MetricsCollector):
    eval_pessoa_fields(gt, pred, context, pid, col)
    v_fields = ['armada', 'arma_da_vítima', 'faleceu', 
                'causa_juridica_da_morte', 'relacao_vitima_autor']
    for f in v_fields:
        eval_value(gt.get(f), pred.get(f), f, context, pid, col)

def eval_resumo(gt: dict, pred: dict, pid: str, col: MetricsCollector):
    gt_r = gt.get('resumo_processo', {}) or {}
    pred_r = pred.get('resumo_processo', {}) or {}
    eval_value(gt_r.get('classificacao_crime'), pred_r.get('classificacao_crime'), 
               'classificacao_crime', 'resumo', pid, col)

def eval_inquerito(gt: dict, pred: dict, pid: str, col: MetricsCollector):
    gt_i = gt.get('inquerito', {}) or {}
    pred_i = pred.get('inquerito', {}) or {}
    
    fields = ['resultado', 'é_feminicidio', 'data_ocorrencia', 'hora_ocorrencia',
              'data_registro', 'delegacia_registro', 'tipo_de_local', 
              'local_detalhado', 'latitude', 'longitude', 'municipio',
              'arma_utilizada', 'bem_roubado', 'natureza_da_autoria',
              'pericia_realizada', 'prisao_em_flagrante', 'razao_arquivamento']
    for f in fields:
        eval_value(gt_i.get(f), pred_i.get(f), f, 'inquerito', pid, col)

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    GT_FILEPATH = "groundtruth_cleaned.json"
    PRED_DIR = "extraction_results"

    try:
        with open(GT_FILEPATH, 'r', encoding='utf-8') as f:
            gt_data = json.load(f)
    except Exception as e:
        print(f"Erro fatal ao carregar GT: {e}")
        return

    if not os.path.exists(PRED_DIR):
        print(f"Pasta '{PRED_DIR}' não encontrada.")
        return

    pred_files = [f for f in os.listdir(PRED_DIR) if f.endswith(".json")]

    if not pred_files:
        print("Nenhum arquivo JSON encontrado em extraction_results/")
        return

    print(f"\nEncontrados {len(pred_files)} arquivos para avaliar.\n")

    for pred_filename in pred_files:

        print("=" * 70)
        print(f"Avaliando arquivo: {pred_filename}")
        print("=" * 70)

        pred_path = os.path.join(PRED_DIR, pred_filename)

        try:
            with open(pred_path, 'r', encoding='utf-8') as f:
                pred_data = json.load(f)
        except Exception as e:
            print(f"Erro ao carregar {pred_filename}: {e}")
            continue

        collector = MetricsCollector()
        failed_processes = []

        for pid, gt_proc in gt_data.items():
            try:
                if pid not in pred_data:
                    continue

                pred_proc = pred_data[pid].get('result', {})

                eval_resumo(gt_proc, pred_proc, pid, collector)
                eval_inquerito(gt_proc, pred_proc, pid, collector)

                gt_vits = gt_proc.get('vítimas', [])
                pred_vits = pred_proc.get('vítimas', {}).get('vitimas', [])
                eval_list_of_objects(gt_vits, pred_vits, eval_vitima, "vítimas", pid, collector)

                gt_susp = gt_proc.get('suspeitos', [])
                pred_susp = pred_proc.get('suspeitos', {}).get('Suspeitos', [])
                eval_list_of_objects(gt_susp, pred_susp, eval_pessoa_fields, "suspeitos", pid, collector)

                gt_test = gt_proc.get('testemunhas', [])
                pred_test = pred_proc.get('testemunhas', {}).get('testemunhas', [])
                eval_list_of_objects(gt_test, pred_test, eval_pessoa_fields, "testemunhas", pid, collector)

            except Exception as e:
                failed_processes.append({
                    "process_id": pid,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
                continue

        # ============================
        # CRIAR PASTA DA ARQUITETURA
        # ============================

        base_name = pred_filename.replace("_results.json", "").replace(".json", "")
        output_dir = base_name

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        csv_path = os.path.join(output_dir, "metricas_brutas.csv")
        json_path = os.path.join(output_dir, "relatorio_final_analitico.json")
        error_path = os.path.join(output_dir, "erros_execucao.json")

        df = collector.get_dataframe()

        if not df.empty:
            df.to_csv(csv_path, index=False)
            collector.save_json_report(json_path)

        if failed_processes:
            with open(error_path, 'w', encoding='utf-8') as f:
                json.dump(failed_processes, f, indent=4, ensure_ascii=False)

        print(f"\nFinalizado: {pred_filename}")
        print(f"Resultados salvos em: {output_dir}\n")

    print("\nComparações completas finalizadas.")
    
if __name__ == "__main__":
    main()