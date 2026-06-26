import os
import json
import pandas as pd

def consolidar_tokens(diretorio_origem, arquivo_saida="consolidado_tokens.csv"):
    """
    Lê todos os JSONs de um diretório que contenham estatísticas de tokens 
    e gera um relatório consolidado.
    """
    dados_consolidados = []
    totais_por_prompt = {}

    # 1. Procurar todos os ficheiros JSON no diretório
    files = [f for f in os.listdir(diretorio_origem) if f.endswith('.json')]
    
    if not files:
        print(f"Nenhum ficheiro JSON encontrado em: {diretorio_origem}")
        return

    print(f"Processando {len(files)} ficheiros...")

    for file in files:
        caminho_completo = os.path.join(diretorio_origem, file)
        
        try:
            with open(caminho_completo, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extrair dados principais
            doc_id = data.get("doc_id", file) # Usa o nome do ficheiro se não houver ID
            total_doc = data.get("total_tokens", 0)
            prompts = data.get("tokens_por_prompt", {})

            # Criar linha para o DataFrame
            row = {
                "doc_id": doc_id,
                "total_tokens": total_doc
            }
            
            # Adicionar tokens de cada prompt individualmente
            for prompt_name, token_count in prompts.items():
                row[f"prompt_{prompt_name}"] = token_count
                
                # Somar para o relatório global
                totais_por_prompt[prompt_name] = totais_por_prompt.get(prompt_name, 0) + token_count
            
            dados_consolidados.append(row)

        except Exception as e:
            print(f"Erro ao processar {file}: {e}")

    # 2. Criar DataFrame e Salvar
    df = pd.DataFrame(dados_consolidados)
    
    # Preencher com 0 campos que não existam em todos os documentos
    df = df.fillna(0)
    
    df.to_csv(arquivo_saida, index=False, encoding='utf-8-sig')
    
    # 3. Exibir Resumo no Terminal
    print("\n" + "="*50)
    print("RESUMO TOTAL DE TOKENS (USO DO MODELO)")
    print("="*50)
    print(f"Total de Documentos: {len(df)}")
    print(f"Total Global de Tokens: {df['total_tokens'].sum():,.0f}")
    print("\n--- Breakdown por Tipo de Prompt ---")
    for prompt, total in totais_por_prompt.items():
        print(f" - {prompt.ljust(20)}: {total:,.0f} tokens")
    print("="*50)
    print(f"Relatório detalhado salvo em: {arquivo_saida}")

if __name__ == "__main__":
    # COLOQUE AQUI O CAMINHO DA PASTA ONDE ESTÃO OS SEUS LOGS DE TOKENS
    DIRETORIO_LOGS = "results_variants_gemini/tokens" 
    
    # Se os tokens estiverem todos dentro de um único arquivo JSON que é uma LISTA:
    # Use o código abaixo em vez de ler o diretório.
    consolidar_tokens(DIRETORIO_LOGS)