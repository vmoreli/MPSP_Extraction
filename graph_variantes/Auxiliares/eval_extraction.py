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

#utils 

import unicodedata

def normalize_string(text: Any) -> str:
    """
    Remove acentos, converte para minúsculas e remove espaços extras.
    Ex: 'Homicídio ' -> 'homicidio'
    """
    if text is None:
        return ""
    s = str(text).lower().strip()
    # Normalização Unicode para remover acentos
    s = unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('ASCII')

    return s

def extract_safe_list(obj_data: Any, keys_to_try: List[str]) -> List[Dict]:
    """Garante que captura uma lista independentemente da estrutura aninhada do JSON."""
    if isinstance(obj_data, list):
        return obj_data
    if isinstance(obj_data, dict):
        for k in keys_to_try:
            if k in obj_data and isinstance(obj_data[k], list):
                return obj_data[k]
    return []
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
        
        # Definição de Acerto para campos estruturados
        field_df['is_correct'] = field_df['result'].isin(['MATCH_EXACT', 'MATCH_SEMANTIC', 'TRUE_NEGATIVE'])

        # --- CÁLCULO DE ACURÁCIA (Global: TP + TN / Total) ---
        accuracy_per_field = field_df.groupby('field')['is_correct'].mean()

        # --- CÁLCULO DE PRECISÃO (Qualidade da Extração: TP / TP + FP) ---
        # Filtramos apenas as linhas onde a IA DE FATO extraiu algum valor (não nulo)
        # Isso exclui os TRUE_NEGATIVES e os FALSE_NEGATIVES da conta.
        prec_df = field_df[field_df['pred_value'].notna()].copy()
        precision_per_field = prec_df.groupby('field')['is_correct'].mean()

        print("\n--- Performance por Campo (Rank: Acurácia) ---")
        # Unimos as métricas em um DataFrame para exibição limpa
        summary_stats = pd.DataFrame({
            'Acurácia': accuracy_per_field,
            'Precisão': precision_per_field,
            'Amostras (N)': field_df.groupby('field').size()
        }).sort_values('Acurácia', ascending=False)
        
        # Preenche com 0.0 campos onde a IA nunca previu nada (evita NaN)
        summary_stats['Precisão'] = summary_stats['Precisão'].fillna(0.0)
        
        print(summary_stats)

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
        field_df['is_correct'] = field_df['result'].isin(['MATCH_EXACT', 'MATCH_SEMANTIC', 'TRUE_NEGATIVE'])
        
        # Séries de cálculo
        accuracy_series = field_df.groupby('field')['is_correct'].mean()
        
        # Precisão: Filtra quem tem predição antes de tirar a média
        prec_df = field_df[field_df['pred_value'].notna()]
        precision_series = prec_df.groupby('field')['is_correct'].mean()
        
        breakdown_df = field_df.groupby(['field', 'result']).size().unstack(fill_value=0)

        fields_list = []
        for field_name, acc in accuracy_series.sort_values(ascending=False).items():
            field_counts = breakdown_df.loc[field_name].to_dict()
            field_counts = {k: int(v) for k, v in field_counts.items() if v > 0}
            
            # Busca a precisão ou define como 0 se não houver predições
            prec = precision_series.get(field_name, 0.0)

            fields_list.append({
                "field": field_name,
                "accuracy": round(float(acc), 4),
                "precision": round(float(prec), 4), # O NOVO CAMPO
                "total_samples": sum(field_counts.values()),
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
        null_synonyms = [
            "não informado", "nao informado", "não informada", "nao", "não", 
            "não identificado", "não identificados", "nao identificado", 
            "nao identificados", "não consta", "nao consta", "não identificada", 
            "não identificadas", "nao identificada", "nao identificadas", 
            "nao informada", "ni", "n/i", "sem informação", "ignorado", 
            "não informados", "não informadas", "nao informados", 
            "nao informadas", "", 
            "não especificada", "não especificado", "não especificadas", 
            "não especificados"
        ]
        if clean_val in null_synonyms: return None
        return val
    return val

def eval_value(gt: Any, pred: Any, field_name: str, context: str, 
               process_id: str, collector: MetricsCollector):

    # =================================================================
    # FILTRO 0: IGNORAR "NÃO APLICÁVEL"
    # =================================================================
    if isinstance(gt, str):
        gt_clean = gt.strip().lower()
        if gt_clean in ["não aplicável", "nao aplicavel", "não se aplica", "nao se aplica"]:
            return  
    
    # 1. Normalização de Nulos (Trata "Não informado" como None)
    gt_treated = treat_null_equivalents(gt)
    pred_treated = treat_null_equivalents(pred)

    # 2. Match de Nulos (Verdadeiro Negativo)
    if gt_treated is None and pred_treated is None:
        collector.log(process_id, context, field_name, gt, pred, "TRUE_NEGATIVE", 1.0)
        return

    # 3. Lógica Booleana (IMPORTANTE: Deve vir antes de normalize_string)
    # Se um for bool, força comparação booleana
    if isinstance(gt_treated, bool) or isinstance(pred_treated, bool):
        val_gt = is_boolean_true(gt_treated)
        val_pred = is_boolean_true(pred_treated)
        if val_gt == val_pred:
            collector.log(process_id, context, field_name, gt, pred, "MATCH_EXACT", 1.0)
        else:
            collector.log(process_id, context, field_name, gt, pred, "VALUE_MISMATCH", 0.0)
        return

    # 4. Erros de Nulo (Missing/Extra Field)
    if gt_treated is not None and pred_treated is None:
        collector.log(process_id, context, field_name, gt, pred, "FALSE_NEGATIVE", 0.0)
        return
    
    if gt_treated is None and pred_treated is not None:
        collector.log(process_id, context, field_name, gt, pred, "FALSE_POSITIVE", 0.0)
        return

    # 5. Normalização de String para comparação exata
    gt_norm = normalize_string(gt_treated)
    pred_norm = normalize_string(pred_treated)

    if gt_norm == pred_norm:
        collector.log(process_id, context, field_name, gt, pred, "MATCH_EXACT", 1.0)
        return

    # 6. Bloqueio de campos estritos
    if field_name in STRICT_FIELDS:
        collector.log(process_id, context, field_name, gt, pred, "VALUE_MISMATCH", 0.0)
        return

    # 7. Similaridade Semântica (Campos não-estritos)
    if isinstance(gt_treated, str) and isinstance(pred_treated, str):
        emb_gt = sentence_embedding(gt_treated)
        emb_pred = sentence_embedding(pred_treated)
        sim = cosine_sim(emb_gt, emb_pred)

        if sim >= SIMILARITY_THRESHOLD:
            collector.log(process_id, context, field_name, gt, pred, "MATCH_SEMANTIC", sim)
        else:
            collector.log(process_id, context, field_name, gt, pred, "VALUE_MISMATCH", sim)
        return

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
    GT_FILEPATH = "cleanGT.json"
    PRED_FILEPATH = "extraction_results/5_nodes_results.json"
    
    try:
        with open(GT_FILEPATH, 'r', encoding='utf-8') as f: gt_data = json.load(f)
        with open(PRED_FILEPATH, 'r', encoding='utf-8') as f: pred_data = json.load(f)
    except Exception as e:
        print(f"Erro fatal ao carregar arquivos de entrada: {e}")
        return

    collector = MetricsCollector()
    failed_processes = [] # Lista para armazenar os erros
    
    print(f"Iniciando avaliação de {len(gt_data)} processos...")

    for pid, gt_proc in gt_data.items():
        # Proteção individual por processo
        try:
            if pid not in pred_data:
                print(f"Processo {pid} ignorado (não está na predição).")
                continue
                
            pred_proc = pred_data[pid].get('result', {})
            print(f"Avaliando Processo {pid}...", end='\r') # end='\r' para não poluir demais o log

            # --- INÍCIO DA AVALIAÇÃO ---
            eval_resumo(gt_proc, pred_proc, pid, collector)
            eval_inquerito(gt_proc, pred_proc, pid, collector)
            
            # 1. VÍTIMAS
            gt_vits = gt_proc.get('vitimas', gt_proc.get('vítimas', [])) # Tenta com e sem acento
            pred_vits_raw = pred_proc.get('vítimas', pred_proc.get('vitimas', []))
            pred_vits = extract_safe_list(pred_vits_raw, ['vitimas', 'vítimas', 'Vitimas'])
            eval_list_of_objects(gt_vits, pred_vits, eval_vitima, "vítimas", pid, collector)
            
            # 2. SUSPEITOS
            gt_susp = gt_proc.get('suspeitos', [])
            pred_susp_raw = pred_proc.get('suspeitos', pred_proc.get('Suspeitos', []))
            pred_susp = extract_safe_list(pred_susp_raw, ['suspeitos', 'Suspeitos', 'autores', 'suspeitos_investigados'])
            eval_list_of_objects(gt_susp, pred_susp, eval_pessoa_fields, "suspeitos", pid, collector)
            
            # 3. TESTEMUNHAS
            gt_test = gt_proc.get('testemunhas', [])
            pred_test_raw = pred_proc.get('testemunhas', pred_proc.get('Testemunhas', []))
            pred_test = extract_safe_list(pred_test_raw, ['testemunhas', 'Testemunhas'])
            eval_list_of_objects(gt_test, pred_test, eval_pessoa_fields, "testemunhas", pid, collector)
            # --- FIM DA AVALIAÇÃO ---

        except Exception as e:
            # Captura o erro, loga no console mas NÃO para o script
            error_msg = str(e)
            print(f"\n[ERRO] Falha ao avaliar processo {pid}: {error_msg}")
            # Opcional: imprime o traceback para ajudar no debug
            # traceback.print_exc() 
            
            failed_processes.append({
                "process_id": pid,
                "error": error_msg,
                "traceback": traceback.format_exc()
            })
            continue

    print("\n" + "="*60)
    print("PROCESSAMENTO FINALIZADO")
    collector.print_summary()
    
    # Configuração de diretórios de saída
    base_filename = os.path.basename(PRED_FILEPATH)
    output_dir_name = base_filename.replace('_results.json', '').replace('.json', '')
    
    if not os.path.exists(output_dir_name):
        os.makedirs(output_dir_name)
        print(f"\nDiretório criado: {output_dir_name}")
    
    csv_path = os.path.join(output_dir_name, "metricas_brutas.csv")
    json_path = os.path.join(output_dir_name, "relatorio_final_analitico.json")
    error_log_path = os.path.join(output_dir_name, "erros_execucao.json")

    # Salvando CSV e JSON normais
    df = collector.get_dataframe()
    if not df.empty:
        df.to_csv(csv_path, index=False)
        print(f"CSV salvo em: '{csv_path}'")
        collector.save_json_report(json_path)
    else:
        print("Aviso: O DataFrame de métricas está vazio (possivelmente todos deram erro ou input vazio).")

    # Salvando Log de Erros (se houver)
    if failed_processes:
        print(f"\nATENÇÃO: {len(failed_processes)} processos falharam durante a avaliação.")
        try:
            with open(error_log_path, 'w', encoding='utf-8') as f:
                json.dump(failed_processes, f, indent=4, ensure_ascii=False)
            print(f"Relatório de erros salvo em: '{error_log_path}'")
        except Exception as e:
            print(f"Erro ao salvar log de falhas: {e}")
    else:
        print("\nSucesso: Nenhum erro de processamento detectado.")

if __name__ == "__main__":
    main()