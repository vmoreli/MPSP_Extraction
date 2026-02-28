import os
import json
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================

BASE_DIR = "."

ARQUITETURAS = [
    "1_node_all",
    "2_nodes_MI_VST",
    "3_nodes_M_I_VST",
    "4_nodes_MI_V_S_T",
    "5_nodes"
]

sns.set_theme(style="whitegrid")
plt.rcParams['figure.dpi'] = 110

ARCHITECTURE_MAP = {
    "1_node_all": ["tudo_em_um"],
    "3_nodes_M_I_VST": ["mapeamento", "inquerito", "envolvidos_vst"],
    "4_nodes_MI_V_S_T": ["mapeamento_inquerito", "vitimas", "suspeitos", "testemunhas"],
    "5_nodes": ["mapeamento", "inquerito", "vitimas", "suspeitos", "testemunhas"]
}

# ==============================================================================
# LOAD
# ==============================================================================

def load_data():

    f1_rows = []
    field_data = {}

    # ===============================
    # 1️⃣ F1 + CAMPOS
    # ===============================
    for arq in ARQUITETURAS:

        relatorio = os.path.join(BASE_DIR, arq, "relatorio_final_analitico.json")

        if os.path.exists(relatorio):
            try:
                with open(relatorio, "r", encoding="utf-8") as f:
                    data = json.load(f)

                f1 = data.get("ner_metrics", {}).get("f1_score", np.nan)
                f1_rows.append({"Arquitetura": arq, "F1-Score": f1})

                field_data[arq] = data.get("fields_performance", {})

            except Exception as e:
                print(f"[ERRO] Problema lendo relatório da arquitetura '{arq}': {e}")

    # ===============================
    # 2️⃣ TOKENS
    # ===============================
    tokens_path = os.path.join(BASE_DIR, "results_variants", "tokens")
    all_token_rows = []

    if not os.path.exists(tokens_path):
        print(f"[AVISO] Pasta de tokens não encontrada: {tokens_path}")
    else:
        for file in os.listdir(tokens_path):

            if not file.endswith(".json"):
                continue

            file_path = os.path.join(tokens_path, file)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data_json = json.load(f)

                # Caso 1: lista com pelo menos 1 elemento
                if isinstance(data_json, list):
                    if len(data_json) == 0:
                        print(f"[AVISO] JSON vazio: {file}")
                        continue
                    tk = data_json[0]

                # Caso 2: dicionário direto
                elif isinstance(data_json, dict):
                    tk = data_json

                else:
                    print(f"[AVISO] Formato inesperado no arquivo: {file}")
                    continue

                row = {
                    "doc_id": tk.get("doc_id"),
                    "total_tokens": tk.get("total_tokens", 0)
                }

                for k, v in tk.get("tokens_por_prompt", {}).items():
                    row[k] = v

                all_token_rows.append(row)

            except json.JSONDecodeError:
                print(f"[ERRO] JSON inválido: {file}")

            except Exception as e:
                print(f"[ERRO] Falha processando {file}: {e}")

    df_tokens_global = pd.DataFrame(all_token_rows)

    # ===============================
    # 3️⃣ Tokens por arquitetura
    # ===============================
    token_data = {}

    for arq, prompts in ARCHITECTURE_MAP.items():

        if df_tokens_global.empty:
            token_data[arq] = pd.DataFrame()
            continue

        valid_prompts = [p for p in prompts if p in df_tokens_global.columns]

        if not valid_prompts:
            print(f"[AVISO] Nenhum prompt encontrado para arquitetura {arq}")
            token_data[arq] = pd.DataFrame()
            continue

        df_arch = df_tokens_global[["doc_id"] + valid_prompts].copy()
        df_arch["total_tokens"] = df_arch[valid_prompts].sum(axis=1)

        token_data[arq] = df_arch

    print("Carga de dados finalizada.")

    return pd.DataFrame(f1_rows), field_data, token_data

# ==============================================================================
# 1️⃣ HEATMAP POR ARQUITETURA
# ==============================================================================

def plot_heatmaps(field_data):

    for arq, fields in field_data.items():

        if not fields:
            continue

        try:
            # fields é uma LISTA de dicts
            df = pd.DataFrame(fields)

            # garantir que as colunas existem
            if "field" not in df.columns or "accuracy" not in df.columns:
                print(f"[AVISO] Estrutura inesperada em {arq}")
                continue

            # manter só o necessário
            df = df[["field", "accuracy"]]

            # ordenar
            df = df.sort_values("accuracy")

            # definir campo como índice
            df = df.set_index("field")

            plt.figure(figsize=(6, 8))
            sns.heatmap(
                df,
                annot=True,
                fmt=".1%",
                cmap="RdYlGn",
                vmin=0,
                vmax=1,
                cbar=False
            )

            plt.title(f"Heatmap - {arq}")
            plt.tight_layout()
            plt.savefig(f"heatmap_{arq}.png")
            plt.close()

        except Exception as e:
            print(f"[ERRO] Falha ao gerar heatmap de {arq}: {e}")

# ==============================================================================
# 2️⃣ DISTRIBUIÇÃO DE TOKENS POR ARQUITETURA
# ==============================================================================

def plot_token_distribution_per_arch(token_data):

    for arch, df_arch in token_data.items():

        if df_arch.empty:
            continue

        arch_total = df_arch["total_tokens"].sort_values().reset_index(drop=True)

        plt.figure(figsize=(8, 5))
        sns.lineplot(x=arch_total.index, y=arch_total.values)

        plt.title(f"Distribuição Ordenada de Tokens - {arch}")
        plt.xlabel("Documento (ordenado)")
        plt.ylabel("Tokens")
        plt.tight_layout()
        plt.savefig(f"distribuicao_tokens_{arch}.png")
        plt.close()


# ==============================================================================
# 3️⃣ F1 COMPARATIVO
# ==============================================================================

def plot_f1_comparison(df_f1):

    if df_f1.empty:
        print("Sem dados de F1.")
        return

    plt.figure(figsize=(8, 5))

    chart = sns.barplot(
        data=df_f1,
        x="Arquitetura",
        y="F1-Score",
        palette="viridis"
    )

    for container in chart.containers:
        chart.bar_label(container, fmt="%.3f")

    plt.ylim(0, 1.1)
    plt.title("F1 Score Comparativo entre Arquiteturas")
    plt.tight_layout()
    plt.savefig("comparativo_f1.png")
    plt.close()


# ==============================================================================
# 4️⃣ MÉDIA TOTAL DE TOKENS POR ARQUITETURA
# ==============================================================================

def plot_mean_tokens_per_arch(token_data):

    rows = []

    for arch, df_arch in token_data.items():

        if df_arch.empty:
            continue

        mean_tokens = df_arch["total_tokens"].mean()

        rows.append({
            "Arquitetura": arch,
            "Média Tokens": mean_tokens
        })

    df_plot = pd.DataFrame(rows)

    if df_plot.empty:
        print("Sem dados de tokens.")
        return

    plt.figure(figsize=(8, 5))
    sns.barplot(data=df_plot, x="Arquitetura", y="Média Tokens")

    plt.title("Média de Tokens por Arquitetura")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("media_tokens_por_arquitetura.png")
    plt.close()


# ==============================================================================
# MAIN
# ==============================================================================

def main():

    df_f1, field_data, token_data = load_data()

    plot_heatmaps(field_data)
    plot_token_distribution_per_arch(token_data)
    plot_f1_comparison(df_f1)
    plot_mean_tokens_per_arch(token_data)

    print("Todos os gráficos foram gerados com sucesso.")


if __name__ == "__main__":
    main()