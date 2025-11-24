import os
import json
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
    # E5 requer prefixo "query:" para buscas assimetricas, mas para comparação direta
    # semântica, o uso puro ou com "passage:" funciona bem. Vamos usar puro aqui.
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
        """
        Registra uma comparação atômica.
        """
        self.records.append({
            "process_id": process_id,
            "context": context,      # Ex: "resumo", "vitimas"
            "field": field,          # Ex: "cor", "idade", "entidade_pessoa"
            "gt_value": str(gt_val) if gt_val is not None else None,
            "pred_value": str(pred_val) if pred_val is not None else None,
            "result": result_tag,    # Taxonomia (MATCH_EXACT, VALUE_MISMATCH...)
            "score": score           # 0.0 a 1.0
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

        # 1. Distribuição de Resultados
        print("\n--- Distribuição de Tags de Erro/Acerto ---")
        print(df['result'].value_counts())

        # 2. Métricas de Entidades (Precision/Recall/F1)
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

        # 3. Acurácia por Campo (excluindo marcadores de entidade)
        # CORREÇÃO AQUI: Adicionado .copy() para evitar o Warning
        field_df = df[~df['field'].str.contains("match_entidade")].copy()
        
        # Definir o que é "Acerto"
        field_df['is_correct'] = field_df['result'].isin(['MATCH_EXACT', 'MATCH_SEMANTIC'])
        
        print("\n--- Acurácia por Campo (Top 10 Piores) ---")
        accuracy_per_field = field_df.groupby('field')['is_correct'].mean().sort_values()
        print(accuracy_per_field.head(10))

    def save_json_report(self, filepath="relatorio_completo.json"):
        """
        Gera um relatório JSON detalhado com estatísticas agregadas.
        """
        df = self.get_dataframe()
        if df.empty:
            print("Não há dados para gerar relatório JSON.")
            return

        report_data = {}

        # =========================================================
        # 1. Resumo Global (Contagem de Tags)
        # =========================================================
        # Converte int64 do pandas para int nativo do Python para serialização JSON
        report_data["global_counts"] = {k: int(v) for k, v in df['result'].value_counts().to_dict().items()}

        # =========================================================
        # 2. Métricas de Entidades (NER)
        # =========================================================
        ent_df = df[df['field'].str.contains("match_entidade")]
        ner_metrics = {
            "precision": 0.0, "recall": 0.0, "f1_score": 0.0,
            "tp": 0, "fp": 0, "fn": 0
        }
        
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

        # =========================================================
        # 3. Detalhamento por Campo (Ordenado por Acurácia)
        # =========================================================
        field_df = df[~df['field'].str.contains("match_entidade")].copy()
        
        # Define o que é acerto
        field_df['is_correct'] = field_df['result'].isin(['MATCH_EXACT', 'MATCH_SEMANTIC'])

        # Agrupa para calcular acurácia média
        accuracy_series = field_df.groupby('field')['is_correct'].mean()
        
        # Agrupa para contar os tipos de erro/acerto por campo
        # Retorna um DataFrame onde índice é o campo e colunas são os tipos de result
        breakdown_df = field_df.groupby(['field', 'result']).size().unstack(fill_value=0)

        fields_list = []
        
        # Ordena crescente (piores primeiro)
        for field_name, acc in accuracy_series.sort_values(ascending=True).items():
            
            # Pega a linha correspondente no breakdown e converte para dicionário
            # Ex: {'MATCH_EXACT': 10, 'FALSE_NEGATIVE': 2}
            field_counts = breakdown_df.loc[field_name].to_dict()
            
            # Remove chaves com valor 0 para limpar o JSON
            field_counts = {k: int(v) for k, v in field_counts.items() if v > 0}
            
            total_samples = sum(field_counts.values())

            fields_list.append({
                "field": field_name,
                "accuracy": round(float(acc), 4),
                "total_samples": total_samples,
                "breakdown": field_counts
            })

        report_data["fields_performance"] = fields_list

        # =========================================================
        # Salvar Arquivo
        # =========================================================
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=4, ensure_ascii=False)
            print(f"\nRelatório JSON salvo com sucesso em: {filepath}")
        except Exception as e:
            print(f"Erro ao salvar relatório JSON: {e}")

# ==============================================================================
# LÓGICA DE COMPARAÇÃO (VALORES)
# ==============================================================================

def treat_null_equivalents(val: Any) -> Any:
    """
    Normaliza valores. Se for string indicando ausência de dados, converte para None.
    """
    if val is None:
        return None
        
    if isinstance(val, str):
        # Remove espaços e coloca em minúsculas
        clean_val = val.lower().strip()
        
        # Lista de variações que significam "Nulo"
        null_synonyms = [
            "não informado", "nao informado",
            "não informada", "nao informada",
            "ni", "n/i", "sem informação", "ignorado"
        ]
        
        if clean_val in null_synonyms:
            return None
            
        return val # Retorna a string original se não for sinônimo de nulo
        
    return val # Retorna o valor original (int, bool, etc)

def eval_value(gt: Any, pred: Any, field_name: str, context: str, 
               process_id: str, collector: MetricsCollector):
    """
    Decide a tag da taxonomia para um par de valores simples.
    Agora suporta equivalência entre 'Não informado' e None.
    """
    
    # 1. Normalização prévia (Trata "Não informado" como None)
    gt_treated = treat_null_equivalents(gt)
    pred_treated = treat_null_equivalents(pred)

    # 2. Se ambos resultaram em None após o tratamento
    # (Isso cobre: None vs None, "Não informado" vs None, "Não informado" vs "Não informada")
    if gt_treated is None and pred_treated is None:
        # Opcional: Se quiser registrar que houve um match de nulos/vazios:
        # collector.log(process_id, context, field_name, gt, pred, "MATCH_NULL", 1.0)
        return # Consideramos acerto silencioso ou ignoramos, conforme sua preferência

    # 3. Erros de Nulo (Omissão ou Alucinação de Campo)
    # Agora só entra aqui se um lado for REALMENTE valor e o outro for None (ou equivalente)
    if gt_treated is not None and pred_treated is None:
        collector.log(process_id, context, field_name, gt, pred, "FALSE_NEGATIVE", 0.0)
        return
    
    if gt_treated is None and pred_treated is not None:
        collector.log(process_id, context, field_name, gt, pred, "FALSE_POSITIVE", 0.0)
        return

    # 4. Match Exato (Prioridade máxima)
    gt_norm = str(gt_treated).lower().strip() if isinstance(gt_treated, str) else gt_treated
    pred_norm = str(pred_treated).lower().strip() if isinstance(pred_treated, str) else pred_treated

    if gt_norm == pred_norm:
        collector.log(process_id, context, field_name, gt, pred, "MATCH_EXACT", 1.0)
        return

    # 5. Strings diferentes -> Tentar Semântica
    if isinstance(gt_treated, str) and isinstance(pred_treated, str):
        emb_gt = sentence_embedding(gt_treated)
        emb_pred = sentence_embedding(pred_treated)
        sim = cosine_sim(emb_gt, emb_pred)

        if sim >= SIMILARITY_THRESHOLD:
            collector.log(process_id, context, field_name, gt, pred, "MATCH_SEMANTIC", sim)
        else:
            collector.log(process_id, context, field_name, gt, pred, "VALUE_MISMATCH", sim)
        return

    # 6. Tipos incompatíveis ou valores numéricos diferentes
    collector.log(process_id, context, field_name, gt, pred, "VALUE_MISMATCH", 0.0)


# ==============================================================================
# LÓGICA DE COMPARAÇÃO (LISTAS E OBJETOS)
# ==============================================================================

def eval_list_of_strings(gt_list: List[str], pred_list: List[str], 
                         field_name: str, context: str, process_id: str, 
                         collector: MetricsCollector):
    """
    Compara listas simples de strings (ex: alias, tipos de crime).
    Usa abordagem "Best Match" guloso.
    """
    gt_list = gt_list or []
    pred_list = pred_list or []
    
    # Copias para não alterar original
    gt_temp = gt_list.copy()
    pred_temp = pred_list.copy()
    
    # 1. Match Exato
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

    # 2. Match Semântico (para o que sobrou)
    matched_gt_indices = set()
    
    for i, g_item in enumerate(gt_temp):
        best_sim = -1
        best_p_idx = -1
        
        g_emb = sentence_embedding(g_item)
        
        for j, p_item in enumerate(pred_temp):
            p_emb = sentence_embedding(p_item)
            sim = cosine_sim(g_emb, p_emb)
            if sim > best_sim:
                best_sim = sim
                best_p_idx = j
        
        if best_sim >= SIMILARITY_THRESHOLD and best_p_idx != -1:
            collector.log(process_id, context, field_name, g_item, pred_temp[best_p_idx], "MATCH_SEMANTIC", best_sim)
            matched_gt_indices.add(i)
            # Removemos da pred_temp (hacky way: set to None to avoid index shift)
            pred_temp[best_p_idx] = None 
        else:
            collector.log(process_id, context, field_name, g_item, None, "VALUE_MISMATCH", best_sim if best_sim > -1 else 0)

    # 3. Extras (O que sobrou em pred_temp e não é None)
    for p_item in pred_temp:
        if p_item is not None:
            collector.log(process_id, context, field_name, None, p_item, "EXTRA_VALUE", 0.0)


def eval_list_of_objects(gt_list: List[Dict], pred_list: List[Dict], 
                         eval_func: Callable, list_name: str, process_id: str, 
                         collector: MetricsCollector):
    """
    Alinha objetos por nome (Exato -> Semântico) e depois compara campos internos.
    Gera métricas de ENTITY_MATCH, ENTITY_MISSING, ENTITY_EXTRA.
    """
    gt_list = gt_list or []
    pred_list = pred_list or []

    gt_matched_indices = set()
    pred_matched_indices = set()
    pairs_to_compare = [] # (gt_item, pred_item, tag_match)

    # --- PASSO 1: Match Exato de Nome ---
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
    
    # --- PASSO 2: Match Semântico de Nome (sobras) ---
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

    # --- REGISTRO DAS MÉTRICAS DE ENTIDADE ---
    
    # 1. Pares Encontrados
    for gt_obj, pred_obj, match_tag in pairs_to_compare:
        # Loga que a entidade foi encontrada (para cálculo de Recall/Precision)
        nome = gt_obj.get('nome')
        collector.log(process_id, list_name, "match_entidade", nome, pred_obj.get('nome'), match_tag)
        
        # Agora compara os campos internos
        # O contexto vira ex: "vitimas[João]"
        sub_context = f"{list_name}[{nome}]"
        eval_func(gt_obj, pred_obj, sub_context, process_id, collector)

    # 2. Missing (Ficaram no GT)
    for i, gt_item in enumerate(gt_list):
        if i not in gt_matched_indices:
            nome = gt_item.get('nome', f"item_{i}")
            collector.log(process_id, list_name, "match_entidade", nome, None, "ENTITY_MISSING", 0.0)

    # 3. Extra (Ficaram na Pred)
    for j, pred_item in enumerate(pred_list):
        if j not in pred_matched_indices:
            nome = pred_item.get('nome', f"item_{j}")
            collector.log(process_id, list_name, "match_entidade", None, nome, "ENTITY_EXTRA", 0.0)

# ==============================================================================
# SCHEMAS DE AVALIAÇÃO
# ==============================================================================

# ------------------------------------------------------------------
# NOVO AUXILIAR PARA LÓGICA BOOLEANA
# ------------------------------------------------------------------
def is_boolean_true(val: Any) -> bool:
    """
    Retorna True apenas se o valor indicar inequivocamente 'Verdadeiro'.
    Trata strings como 'false', 'não', '0' como False.
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

# ------------------------------------------------------------------
# FUNÇÃO DE AVALIAÇÃO DE PESSOA (COM LÓGICA CONDICIONAL)
# ------------------------------------------------------------------
def eval_pessoa_fields(gt: dict, pred: dict, context: str, pid: str, col: MetricsCollector):
    """
    Avalia campos de pessoa com lógica de dependência:
    Se 'é_policial' for Falso em ambos, ignora corporação e status de serviço.
    """
    
    # 1. Campos Gerais (Sempre avaliados)
    common_fields = ['cor', 'sexo', 'profissao', 'escolaridade', 
                     'nacionalidade', 'idade', 'antecedentes_criminais']
    
    for f in common_fields:
        eval_value(gt.get(f), pred.get(f), f, context, pid, col)

    # 2. Avaliação do Status 'é_policial'
    # Avaliamos explicitamente primeiro para gerar a métrica deste campo
    gt_is_police_raw = gt.get('é_policial')
    pred_is_police_raw = pred.get('é_policial')
    
    eval_value(gt_is_police_raw, pred_is_police_raw, 'é_policial', context, pid, col)

    # 3. Campos Condicionais (Só avalia se necessário)
    police_fields = ['corporacao_policial', 'policial_em_servico']
    
    # Normaliza para booleano python puro para decidir a lógica
    gt_bool = is_boolean_true(gt_is_police_raw)
    pred_bool = is_boolean_true(pred_is_police_raw)

    # LÓGICA DE NEGÓCIO:
    # Se GT diz que NÃO é policial E Pred diz que NÃO é policial -> Pula validação dos detalhes
    # Isso evita comparar "não é policial" (GT) com None (Pred), o que gerava erro.
    if not gt_bool and not pred_bool:
        # Opcional: Se você quiser registrar explicitamente que foi ignorado/acertado por lógica:
        # for f in police_fields:
        #     col.log(pid, context, f, "N/A", "N/A", "MATCH_LOGIC", 1.0)
        pass 
    else:
        # Se pelo menos um diz que é policial, ou há discordância, avaliamos os detalhes
        # para pegar potenciais erros de conteúdo ou alucinações.
        for f in police_fields:
            eval_value(gt.get(f), pred.get(f), f, context, pid, col)

def eval_vitima(gt: dict, pred: dict, context: str, pid: str, col: MetricsCollector):
    # Campos base de Pessoa
    eval_pessoa_fields(gt, pred, context, pid, col)
    # Campos específicos de Vítima
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
    # SETUP
    GT_FILEPATH = "groundtruth_cleaned.json"
    PRED_FILEPATH = "output/run_2025-11-05_15-36-36/st_5_sabiazinho-3_results.json"
    
    try:
        with open(GT_FILEPATH, 'r', encoding='utf-8') as f: gt_data = json.load(f)
        with open(PRED_FILEPATH, 'r', encoding='utf-8') as f: pred_data = json.load(f)
    except Exception as e:
        print(f"Erro ao carregar arquivos: {e}")
        return

    collector = MetricsCollector()
    
    # EXECUÇÃO
    for pid, gt_proc in gt_data.items():
        if pid not in pred_data:
            print(f"Processo {pid} ignorado (não está na predição).")
            continue
            
        pred_proc = pred_data[pid].get('result', {})
        
        print(f"Avaliando Processo {pid}...")

        # 1. Estruturas Estáticas
        eval_resumo(gt_proc, pred_proc, pid, collector)
        eval_inquerito(gt_proc, pred_proc, pid, collector)
        
        # 2. Listas Dinâmicas (Entidades)
        # Vítimas
        gt_vits = gt_proc.get('vítimas', [])
        pred_vits = pred_proc.get('vítimas', {}).get('vitimas', [])
        eval_list_of_objects(gt_vits, pred_vits, eval_vitima, "vítimas", pid, collector)
        
        # Suspeitos
        gt_susp = gt_proc.get('suspeitos', [])
        pred_susp = pred_proc.get('suspeitos', {}).get('Suspeitos', [])
        eval_list_of_objects(gt_susp, pred_susp, eval_pessoa_fields, "suspeitos", pid, collector)
        
        # Testemunhas
        gt_test = gt_proc.get('testemunhas', [])
        pred_test = pred_proc.get('testemunhas', {}).get('testemunhas', [])
        eval_list_of_objects(gt_test, pred_test, eval_pessoa_fields, "testemunhas", pid, collector)

    # RELATÓRIOS FINAIS
    collector.print_summary()
    
    # --- LÓGICA DE CRIAÇÃO DO DIRETÓRIO DE SAÍDA ---
    
    # 1. Pega apenas o nome do arquivo (st_5_sabiazinho-3_results.json)
    base_filename = os.path.basename(PRED_FILEPATH)
    
    # 2. Remove a extensão .json e o sufixo _results
    # O replace garante que limpamos o sufixo conforme pedido
    output_dir_name = base_filename.replace('_results.json', '').replace('.json', '')
    
    # 3. Cria o diretório se não existir
    if not os.path.exists(output_dir_name):
        os.makedirs(output_dir_name)
        print(f"\nDiretório criado: {output_dir_name}")
    
    # 4. Define os caminhos finais dentro desse diretório
    csv_path = os.path.join(output_dir_name, "metricas_brutas.csv")
    json_path = os.path.join(output_dir_name, "relatorio_final_analitico.json")

    # Salvar CSV (dados brutos)
    df = collector.get_dataframe()
    df.to_csv(csv_path, index=False)
    print(f"CSV salvo em: '{csv_path}'")
    
    # Salvar JSON (Relatório Analítico)
    collector.save_json_report(json_path)

if __name__ == "__main__":
    main()