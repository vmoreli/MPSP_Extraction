import os
import json
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

# ==============================================================================
# 1. CONFIGURAÇÕES DE ENTRADA
# ==============================================================================

# Preencha aqui conforme a estrutura de pastas que você gerou
# Exemplo: pasta "st_5_gemini-1.5-flash" -> modo="st_5", modelo="gemini-1.5-flash"
MODOS = ["st_5"] 
MODELOS = ["gemini-2.5-flash", "gemini-2.5-pro", "sabiazinho-3", "sabia-3.1"]

# Diretório base onde estão as pastas (use "." se estiver na mesma raiz)
BASE_DIR = "." 

# Configuração visual
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = [12, 6]
plt.rcParams['figure.dpi'] = 100

# ==============================================================================
# 2. CARREGAMENTO DE DADOS
# ==============================================================================

def load_data(modos, modelos):
    ner_records = []
    error_dist_records = []
    field_accuracy_records = []

    for modo in modos:
        for modelo in modelos:
            folder_name = f"{modo}_{modelo}" # Ajuste se o padrão de nome for diferente
            folder_path = os.path.join(BASE_DIR, folder_name)
            
            json_path = os.path.join(folder_path, "relatorio_final_analitico.json")
            csv_path = os.path.join(folder_path, "metricas_brutas.csv")

            if not os.path.exists(json_path) or not os.path.exists(csv_path):
                print(f"[AVISO] Resultados não encontrados para: {folder_name} (pulando)")
                continue
            
            print(f"Carregando: {folder_name}")

            # 1. Carregar JSON (NER e Totais)
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data_json = json.load(f)
                
                # Extrair Métricas NER
                ner = data_json.get("ner_metrics", {})
                ner_records.append({
                    "Modo": modo,
                    "Modelo": modelo,
                    "ID": f"{modelo}\n({modo})",
                    "Precision": ner.get("precision", 0),
                    "Recall": ner.get("recall", 0),
                    "F1-Score": ner.get("f1_score", 0)
                })

                # Extrair Distribuição Global de Erros (Normalizada %)
                counts = data_json.get("global_counts", {})
                total = sum(counts.values()) if counts else 1
                
                # Agrupando tipos de erro para simplificar o gráfico
                error_dist_records.append({
                    "ID": f"{modelo} ({modo})",
                    "Acerto (Exato+Semântico)": (counts.get("MATCH_EXACT", 0) + counts.get("MATCH_SEMANTIC", 0) + 
                                                 counts.get("ENTITY_MATCH_EXACT", 0) + counts.get("ENTITY_MATCH_SEMANTIC", 0)) / total,
                    "Valor Incorreto": (counts.get("VALUE_MISMATCH", 0)) / total,
                    "Omissão (Missing)": (counts.get("FALSE_NEGATIVE", 0) + counts.get("ENTITY_MISSING", 0)) / total,
                    "Alucinação (Extra)": (counts.get("FALSE_POSITIVE", 0) + counts.get("ENTITY_EXTRA", 0)) / total
                })

            except Exception as e:
                print(f"Erro ao ler JSON de {folder_name}: {e}")

            # 2. Carregar CSV (Acurácia detalhada por campo)
            try:
                df_csv = pd.read_csv(csv_path)
                # Filtra apenas campos de valor (ignora match de entidade para focar em campos)
                df_fields = df_csv[~df_csv['field'].str.contains("match_entidade")].copy()
                
                # Define o que é acerto
                df_fields['acertou'] = df_fields['result'].isin(['MATCH_EXACT', 'MATCH_SEMANTIC'])
                
                # Calcula média por campo
                acc_by_field = df_fields.groupby('field')['acertou'].mean().reset_index()
                acc_by_field['Modo'] = modo
                acc_by_field['Modelo'] = modelo
                
                field_accuracy_records.append(acc_by_field)

            except Exception as e:
                print(f"Erro ao ler CSV de {folder_name}: {e}")

    return {
        "ner": pd.DataFrame(ner_records),
        "errors": pd.DataFrame(error_dist_records).set_index("ID"),
        "fields": pd.concat(field_accuracy_records) if field_accuracy_records else pd.DataFrame()
    }

# ==============================================================================
# 3. VISUALIZAÇÕES
# ==============================================================================

def plot_ner_comparison(df_ner):
    if df_ner.empty: return

    plt.figure(figsize=(10, 6))
    chart = sns.barplot(
        data=df_ner, 
        x="Modelo", 
        y="F1-Score", 
        hue="Modo", 
        palette="viridis"
    )
    
    plt.title("Comparativo de NER (F1-Score) - Extração de Entidades", fontsize=14, fontweight='bold')
    plt.ylim(0, 1.1)
    
    # Adicionar valores nas barras
    for container in chart.containers:
        chart.bar_label(container, fmt='%.2f', padding=3)

    plt.legend(title="Modo/Prompt", loc='lower right')
    plt.tight_layout()
    plt.savefig("comparativo_ner_f1.png")
    print("Gráfico salvo: comparativo_ner_f1.png")
    plt.show()

def plot_error_distribution(df_errors):
    if df_errors.empty: return
    
    # Reordenar colunas para lógica visual (Acerto primeiro, depois erros)
    cols = ["Acerto (Exato+Semântico)", "Valor Incorreto", "Omissão (Missing)", "Alucinação (Extra)"]
    # Garante que existem no df
    cols = [c for c in cols if c in df_errors.columns]
    
    df_plot = df_errors[cols] * 100 # Converter para %

    ax = df_plot.plot(
        kind='barh', 
        stacked=True, 
        color=['#2ecc71', '#f1c40f', '#e74c3c', '#9b59b6'], 
        figsize=(12, 6)
    )

    plt.title("Distribuição de Tipos de Resultado (%)", fontsize=14, fontweight='bold')
    plt.xlabel("Porcentagem do Total de Campos Avaliados")
    plt.ylabel("Modelo (Modo)")
    
    # Adicionar legenda fora
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()
    plt.savefig("distribuicao_erros.png")
    print("Gráfico salvo: distribuicao_erros.png")
    plt.show()

def plot_field_heatmap(df_fields):
    if df_fields.empty: return

    # Pivotar: Linhas=Campos, Colunas=Modelo(Modo), Valor=Acurácia
    df_fields['ID'] = df_fields['Modelo'] + " (" + df_fields['Modo'] + ")"
    pivot_df = df_fields.pivot(index='field', columns='ID', values='acertou')
    
    # Ordenar campos pelo "mais difícil" (menor média geral)
    pivot_df['mean_acc'] = pivot_df.mean(axis=1)
    pivot_df = pivot_df.sort_values('mean_acc', ascending=True)
    pivot_df = pivot_df.drop(columns=['mean_acc'])

    # Se houver muitos campos, pegar os Top 20 mais difíceis
    if len(pivot_df) > 20:
        print(f"Exibindo os 20 campos com pior desempenho (de {len(pivot_df)} totais).")
        pivot_df = pivot_df.head(20)

    plt.figure(figsize=(12, 10))
    sns.heatmap(
        pivot_df, 
        annot=True, 
        fmt=".1%", 
        cmap="RdYlGn", 
        vmin=0, 
        vmax=1, 
        linewidths=.5
    )
    
    plt.title("Heatmap de Acurácia por Campo (Top 20 Mais Difíceis)", fontsize=14, fontweight='bold')
    plt.ylabel("Campo")
    plt.xlabel("Modelo")
    
    plt.tight_layout()
    plt.savefig("heatmap_acuracia_campos.png")
    print("Gráfico salvo: heatmap_acuracia_campos.png")
    plt.show()

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("--- Iniciando Consolidação de Resultados ---")
    data = load_data(MODOS, MODELOS)

    if data["ner"].empty and data["fields"].empty:
        print("Nenhum dado foi carregado. Verifique os caminhos e nomes das pastas.")
        return

    print("\nGerando Gráfico de NER...")
    plot_ner_comparison(data["ner"])

    print("\nGerando Gráfico de Distribuição de Erros...")
    plot_error_distribution(data["errors"])

    print("\nGerando Heatmap de Campos...")
    plot_field_heatmap(data["fields"])
    
    print("\nProcesso concluído.")

if __name__ == "__main__":
    main()