import json
from typing import List, Dict, Any, Callable
from difflib import SequenceMatcher
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# ----------------------------------------------------------------------------
# Constante de Similaridade
# ----------------------------------------------------------------------------
# Define o quão similar (0.0 a 1.0) duas strings precisam ser 
SIMILARITY_THRESHOLD = 0.8

# ============================================================
# EMBEDDINGS
# ============================================================

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

# ----------------------------------------------------------------------------
# Funções de Comparação
# ----------------------------------------------------------------------------

def compare_strings_with_similarity(gt_str: str, pred_str: str, field_name: str, process_id: str):
    """
    Compara duas strings:
    - Se forem idênticas (após normalização), retorna 1.0.
    - Caso contrário, calcula similaridade semântica via embeddings.
    """
    # Normaliza as strings
    gt_clean = gt_str.lower().strip()
    pred_clean = pred_str.lower().strip()

    # Verifica igualdade exata
    if gt_clean == pred_clean:
        print(f"[OK]         {process_id} | {field_name}: '{gt_str}'")
        return 1.0

    # Se não forem idênticas, calcula similaridade via embeddings
    emb_gt = sentence_embedding(gt_clean)
    emb_pred = sentence_embedding(pred_clean)
    ratio_emb = cosine_sim(emb_gt, emb_pred)

    # Log de resultado
    if ratio_emb >= SIMILARITY_THRESHOLD:
        print(
            f"[OK-SIMILAR] {process_id} | {field_name}: "
            f"(EmbSim: {ratio_emb:.2f}) GT='{gt_str}' ~ PRED='{pred_str}'"
        )
    else:
        print(
            f"[MISMATCH]   {process_id} | {field_name}: "
            f"(EmbSim: {ratio_emb:.2f}) GT='{gt_str}' != PRED='{pred_str}'"
        )

    return ratio_emb

def compare_values(gt_val: Any, pred_val: Any, field_name: str, process_id: str):
    """
    Roteador de Comparação:
    - Compara valores perfeitamente.
    - Se ambos forem strings e não idênticos, usa a função de similaridade.
    - Caso contrário, marca como mismatch.
    """
    
    # 1. Checa igualdade perfeita primeiro.
    # Isto resolve None == None, True == True, 10 == 10, e strings 100% idênticas.
    if gt_val == pred_val:
        if gt_val is not None:
             print(f"[OK]       {process_id} | {field_name}: '{gt_val}'")
        # else:
        #     print(f"[OK-N/A]   {process_id} | {field_name}: N/A")
        return # Encontrou um acerto, não precisa de mais nada.

    # 2. Se não são idênticos, vamos checar se AMBOS são strings
    if isinstance(gt_val, str) and isinstance(pred_val, str):
        # Se sim, chama a lógica de similaridade
        compare_strings_with_similarity(gt_val, pred_val, field_name, process_id)
        return

    # 3. Se chegamos aqui, eles são diferentes E não são (ambos strings).
    # Exemplos:
    # - str vs None
    # - int vs str
    # - int vs int (valores diferentes)
    # - bool vs None
    # Todos são Mismatches diretos.
    gt_str = f"'{gt_val}'" if gt_val is not None else "N/A"
    pred_str = f"'{pred_val}'" if pred_val is not None else "N/A"
    print(f"[MISMATCH] {process_id} | {field_name}: GT={gt_str} != PRED={pred_str}")

# ----------------------------------------------------------------------------
# Funções de Comparação de Listas (Sem alteração)
# ----------------------------------------------------------------------------

def compare_list_of_strings(gt_list: List[str], pred_list: List[str], prefix: str, process_id: str):
    """
    Compara duas listas de strings (ex: nomes de pessoas_envolvidas),
    considerando similaridade semântica entre os itens.
    - Ignora a ordem dos elementos.
    - Usa a função compare_strings_with_similarity() para comparação item a item.
    """
    gt_list = gt_list or []
    pred_list = pred_list or []

    # Se ambas estiverem vazias
    if not gt_list and not pred_list:
        print(f"[OK]       {process_id} | {prefix}: Ambas listas vazias")
        return 1.0

    # Guarda correspondências encontradas
    matched_gt = set()
    matched_pred = set()

    # Compara cada elemento de GT com os de Pred
    for gt_item in gt_list:
        for pred_item in pred_list:
            sim = compare_strings_with_similarity(gt_item, pred_item, prefix, process_id)
            if sim >= SIMILARITY_THRESHOLD:
                matched_gt.add(gt_item)
                matched_pred.add(pred_item)
                break  # já encontrou correspondência, passa pro próximo gt_item

    # Identifica itens que não tiveram correspondência suficiente
    missing_in_pred = [x for x in gt_list if x not in matched_gt]
    extra_in_pred = [x for x in pred_list if x not in matched_pred]

    # Resultado geral
    if not missing_in_pred and not extra_in_pred:
        print(f"[OK]       {process_id} | {prefix}: Listas coincidem (Total: {len(gt_list)})")
        return 1.0
    else:
        print(f"[MISMATCH] {process_id} | {prefix}: Listas divergem")
        if missing_in_pred:
            print(f"    -> AUSENTE NA PREDIÇÃO (só GT): {missing_in_pred}")
        if extra_in_pred:
            print(f"    -> EXTRA NA PREDIÇÃO (só PRED): {extra_in_pred}")
        return 0.0

def compare_list_of_objects(gt_list: List[Dict], pred_list: List[Dict], 
                          compare_func: Callable, prefix: str, process_id: str):
    """
    Compara duas listas de objetos (Pessoa, Vitima).
    Usa o 'nome' como chave para parear os objetos.
    """
    gt_list = gt_list or []
    pred_list = pred_list or []

    gt_map = {item.get('nome') or f"item_{i}": item for i, item in enumerate(gt_list)}
    pred_map = {item.get('nome') or f"item_{i}": item for i, item in enumerate(pred_list)}
    
    all_keys = set(gt_map.keys()) | set(pred_map.keys())
    
    if not all_keys:
        print(f"[OK-N/A]   {process_id} | {prefix}: Ambas as listas estão vazias.")
        return

    compare_values(len(gt_list), len(pred_list), f"Contagem de {prefix}", process_id)

    for key in sorted(all_keys):
        gt_item = gt_map.get(key)
        pred_item = pred_map.get(key)
        item_prefix = f"{prefix}[nome={key}]"
        
        if gt_item and pred_item:
            compare_func(gt_item, pred_item, item_prefix, process_id)
        elif gt_item:
            print(f"[MISSING]  {process_id} | {item_prefix}: Encontrado no GT, mas AUSENTE na PREDIÇÃO")
        else:
            print(f"[EXTRA]    {process_id} | {item_prefix}: Encontrado na PREDIÇÃO, mas AUSENTE no GT")

# ----------------------------------------------------------------------------
# Funções de Comparação de Schemas (Sem alteração)
# ----------------------------------------------------------------------------

def compare_pessoa(gt: dict, pred: dict, prefix: str, process_id: str):
    """
    Compara explicitamente cada campo do schema 'Pessoa'.
    """
    print(f"\n--- Comparando {prefix} ---")
    
    compare_values(gt.get('nome'), pred.get('nome'), f"{prefix}.nome", process_id)
    compare_values(gt.get('cor'), pred.get('cor'), f"{prefix}.cor", process_id)
    compare_values(gt.get('sexo'), pred.get('sexo'), f"{prefix}.sexo", process_id)
    compare_values(gt.get('é_policial'), pred.get('é_policial'), f"{prefix}.é_policial", process_id)
    compare_values(gt.get('corporacao_policial'), pred.get('corporacao_policial'), f"{prefix}.corporacao_policial", process_id)
    compare_values(gt.get('policial_em_servico'), pred.get('policial_em_servico'), f"{prefix}.policial_em_servico", process_id)
    compare_values(gt.get('profissao'), pred.get('profissao'), f"{prefix}.profissao", process_id)
    compare_values(gt.get('escolaridade'), pred.get('escolaridade'), f"{prefix}.escolaridade", process_id)
    compare_values(gt.get('nacionalidade'), pred.get('nacionalidade'), f"{prefix}.nacionalidade", process_id)
    compare_values(gt.get('idade'), pred.get('idade'), f"{prefix}.idade", process_id)
    compare_values(gt.get('antecedentes_criminais'), pred.get('antecedentes_criminais'), f"{prefix}.antecedentes_criminais", process_id)

def compare_vitima(gt: dict, pred: dict, prefix: str, process_id: str):
    """
    Compara explicitamente cada campo do schema 'Vitima'.
    """
    compare_pessoa(gt, pred, prefix, process_id)
    
    print(f"--- (Campos Específicos de Vítima para {prefix}) ---")
    
    compare_values(gt.get('armada'), pred.get('armada'), f"{prefix}.armada", process_id)
    compare_values(gt.get('arma_da_vítima'), pred.get('arma_da_vítima'), f"{prefix}.arma_da_vítima", process_id)
    compare_values(gt.get('faleceu'), pred.get('faleceu'), f"{prefix}.faleceu", process_id)
    compare_values(gt.get('causa_juridica_da_morte'), pred.get('causa_juridica_da_morte'), f"{prefix}.causa_juridica_da_morte", process_id)
    compare_values(gt.get('relacao_vitima_autor'), pred.get('relacao_vitima_autor'), f"{prefix}.relacao_vitima_autor", process_id)

def compare_resumo_processo(gt: dict, pred: dict, process_id: str):
    """
    Compara os campos do schema 'ResumoProcesso'.
    """
    print(f"\n{'*' * 10} Comparando ResumoProcesso {'*' * 10}")
    
    gt_resumo = gt.get('resumo_processo', {}) or {}
    pred_resumo = pred.get('resumo_processo', {}) or {}
    
    compare_values(
        gt_resumo.get('classificacao_crime'), 
        pred_resumo.get('classificacao_crime'), 
        "resumo_processo.classificacao_crime", 
        process_id
    )
    
    gt_pessoas = gt_resumo.get('pessoas_envolvidas', {}) or {}
    pred_pessoas = pred_resumo.get('pessoas_envolvidas', {}) or {}
    
    compare_list_of_strings(
        gt_pessoas.get('vitimas'), 
        pred_pessoas.get('vitimas'), 
        "resumo_processo.pessoas_envolvidas.vitimas", 
        process_id
    )
    compare_list_of_strings(
        gt_pessoas.get('suspeitos_investigados'), 
        pred_pessoas.get('suspeitos_investigados'), 
        "resumo_processo.pessoas_envolvidas.suspeitos_investigados", 
        process_id
    )
    compare_list_of_strings(
        gt_pessoas.get('testemunhas'), 
        pred_pessoas.get('testemunhas'), 
        "resumo_processo.pessoas_envolvidas.testemunhas", 
        process_id
    )

def compare_inquerito(gt: dict, pred: dict, process_id: str):
    """
    Compara os campos do schema 'Inquerito'.
    """
    print(f"\n{'*' * 10} Comparando Inquerito {'*' * 10}")
    
    gt_inquerito = gt.get('inquerito', {}) or {}
    pred_inquerito = pred.get('inquerito', {}) or {}
    
    # --- Campos de Classificação ---
    compare_values(gt_inquerito.get('resultado'), pred_inquerito.get('resultado'), "inquerito.resultado", process_id)
    compare_values(gt_inquerito.get('é_feminicidio'), pred_inquerito.get('é_feminicidio'), "inquerito.é_feminicidio", process_id)
    
    # --- Campos de Contexto ---
    compare_values(gt_inquerito.get('data_ocorrencia'), pred_inquerito.get('data_ocorrencia'), "inquerito.data_ocorrencia", process_id)
    compare_values(gt_inquerito.get('hora_ocorrencia'), pred_inquerito.get('hora_ocorrencia'), "inquerito.hora_ocorrencia", process_id)
    compare_values(gt_inquerito.get('data_registro'), pred_inquerito.get('data_registro'), "inquerito.data_registro", process_id)
    compare_values(gt_inquerito.get('delegacia_registro'), pred_inquerito.get('delegacia_registro'), "inquerito.delegacia_registro", process_id)
    
    # --- Campos de Localização ---
    compare_values(gt_inquerito.get('tipo_de_local'), pred_inquerito.get('tipo_de_local'), "inquerito.tipo_de_local", process_id)
    compare_values(gt_inquerito.get('local_detalhado'), pred_inquerito.get('local_detalhado'), "inquerito.local_detalhado", process_id)
    compare_values(gt_inquerito.get('latitude'), pred_inquerito.get('latitude'), "inquerito.latitude", process_id)
    compare_values(gt_inquerito.get('longitude'), pred_inquerito.get('longitude'), "inquerito.longitude", process_id)
    compare_values(gt_inquerito.get('municipio'), pred_inquerito.get('municipio'), "inquerito.municipio", process_id)
    
    # --- Campos de Evidências ---
    compare_values(gt_inquerito.get('arma_utilizada'), pred_inquerito.get('arma_utilizada'), "inquerito.arma_utilizada", process_id)
    compare_values(gt_inquerito.get('bem_roubado'), pred_inquerito.get('bem_roubado'), "inquerito.bem_roubado", process_id)
    
    # --- Campos do Andamento do Inquérito ---
    compare_values(gt_inquerito.get('natureza_da_autoria'), pred_inquerito.get('natureza_da_autoria'), "inquerito.natureza_da_autoria", process_id)
    compare_values(gt_inquerito.get('pericia_realizada'), pred_inquerito.get('pericia_realizada'), "inquerito.pericia_realizada", process_id)
    compare_values(gt_inquerito.get('prisao_em_flagrante'), pred_inquerito.get('prisao_em_flagrante'), "inquerito.prisao_em_flagrante", process_id)
    compare_values(gt_inquerito.get('razao_arquivamento'), pred_inquerito.get('razao_arquivamento'), "inquerito.razao_arquivamento", process_id)

# ----------------------------------------------------------------------------
# Função Principal de Orquestração
# ----------------------------------------------------------------------------

def compare_process_data(process_id: str, gt_proc: dict, pred_proc: dict):
    """
    Orquestra a comparação para um único processo.
    (Esta função foi corrigida para acessar as listas corretamente)
    """
    print(f"\n{'=' * 20} COMPARANDO PROCESSO: {process_id} {'=' * 20}")
    
    # 1. Comparar 'resumo_processo' (Schema ResumoProcesso)
    compare_resumo_processo(gt_proc, pred_proc, process_id)
    
    # 2. Comparar 'inquerito' (Schema Inquerito)
    compare_inquerito(gt_proc, pred_proc, process_id)
    
    # 3. Comparar 'vítimas' (Schema Vitimas -> List[Vitima])
    print(f"\n{'*' * 10} Comparando Lista de Vítimas {'*' * 10}")

    gt_vitimas_list = gt_proc.get('vítimas', {}) or {}
    pred_vitimas_obj = pred_proc.get('vítimas', {}) or {}
    
    pred_vitimas_list = pred_vitimas_obj.get('vitimas', [])
    
    compare_list_of_objects(
        gt_vitimas_list, 
        pred_vitimas_list, 
        compare_vitima, 
        "vítimas.vitimas", 
        process_id
    )
    
    # 4. Comparar 'suspeitos' (Schema Suspeitos -> List[Pessoa])
    print(f"\n{'*' * 10} Comparando Lista de Suspeitos {'*' * 10}")

    gt_suspeitos_list = gt_proc.get('suspeitos', {}) or {}
    pred_suspeitos_obj = pred_proc.get('suspeitos', {}) or {}
    
    pred_suspeitos_list = pred_suspeitos_obj.get('Suspeitos', [])
    
    compare_list_of_objects(
        gt_suspeitos_list, 
        pred_suspeitos_list, 
        compare_pessoa, 
        "suspeitos.Suspeitos", 
        process_id
    )

    # 5. Comparar 'testemunhas' (Schema Testemunhas -> List[Pessoa])
    print(f"\n{'*' * 10} Comparando Lista de Testemunhas {'*' * 10}")
    
    gt_testemunhas_list = gt_proc.get('testemunhas', {}) or {}
    pred_testemunhas_obj = pred_proc.get('testemunhas', {}) or {}
    
    pred_testemunhas_list = pred_testemunhas_obj.get('testemunhas', [])
    
    compare_list_of_objects(
        gt_testemunhas_list, 
        pred_testemunhas_list, 
        compare_pessoa, 
        "testemunhas.testemunhas", 
        process_id
    )

# ----------------------------------------------------------------------------
# Execução (Main)
# ----------------------------------------------------------------------------

def load_json_file(filepath: str) -> Dict:
    """Carrega um arquivo JSON com tratamento de erro."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Erro: Arquivo não encontrado: {filepath}")
        return None
    except json.JSONDecodeError:
        print(f"Erro: Falha ao decodificar JSON em: {filepath}")
        return None
    except Exception as e:
        print(f"Erro inesperado ao ler {filepath}: {e}")
        return None

def main():
    # --- DEFINA OS CAMINHOS DOS ARQUIVOS AQUI ---
    GT_FILEPATH = "groundtruth_cleaned.json"
    PRED_FILEPATH = "output/run_2025-11-05_15-36-36/st_5_sabiazinho-3_results.json"
    # ----------------------------------------------
    
    print(f"Carregando Ground Truth de: {GT_FILEPATH}")
    gt_data = load_json_file(GT_FILEPATH)
    
    print(f"Carregando Predição de:    {PRED_FILEPATH}")
    pred_data = load_json_file(PRED_FILEPATH)
    
    if not gt_data or not pred_data:
        print("Erro ao carregar arquivos. Abortando.")
        return
        
    print("\nIniciando comparação...")
    
    total_processos = 0
    processos_nao_encontrados_pred = 0
    
    for process_id, gt_processo in gt_data.items():
        total_processos += 1
        
        if process_id not in pred_data:
            print(f"\n[ERROR] Processo {process_id} encontrado no GT, mas AUSENTE na PREDIÇÃO.")
            processos_nao_encontrados_pred += 1
            continue
            
        pred_processo_nested = pred_data[process_id]
        
        if 'result' not in pred_processo_nested:
            print(f"\n[ERROR] Processo {process_id} na PREDIÇÃO não contém a chave 'result'. Pulando.")
            continue
            
        pred_processo = pred_processo_nested['result']
        
        compare_process_data(process_id, gt_processo, pred_processo)
        
    print(f"\n{'=' * 50}")
    print("Comparação Concluída.")
    print(f"Total de processos no Ground Truth: {total_processos}")
    print(f"Processos não encontrados na Predição: {processos_nao_encontrados_pred}")
    
    extra_processos = set(pred_data.keys()) - set(gt_data.keys())
    if extra_processos:
        print(f"Processos EXTRA (apenas na Predição): {len(extra_processos)}")


if __name__ == "__main__":
    main()