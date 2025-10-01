# Análise e Seleção do Conjunto de Dados para o Pipeline

## --- Funil de Seleção de Documentos ---

[PASSO 1] Ponto de Partida: Assuntos de Interesse
  - Total de processos de interesse (ex: 'homicídio') definidos nos arquivos de filtro: 117,079

[PASSO 2] Filtro de Disponibilidade: Documentos encontrados e com parsing bem-sucedido
  - Destes, 48,263 foram encontrados em disco E tiveram o parsing inicial bem-sucedido (possuem pasta e .txt).
  └─ Descarte: 68,816 processos foram descartados (não encontrados ou falha no parsing).

[PASSO 3] Filtro de Qualidade: Exclusão de outliers de tokens
  - Deste grupo, 1,059 processos foram removidos por estarem na lista de exclusão (outliers).


Resultado Final: 47,204 processos estão aptos para a execução.


## --- Sumário Executivo ---

+------------------------------------------------------+
| NÚMERO FINAL DE PROCESSOS A SEREM EXECUTADOS: 47204 |
+------------------------------------------------------+

[!] INSIGHTS ACIONÁVEIS:
1. FALHA GERAL DE PARSING: De 82,835 processos baixados, 18,130 falharam no parsing inicial (não geraram .txt).
2. DADOS DE INTERESSE PERDIDOS: 68,816 processos de interesse não puderam ser processados por indisponibilidade ou falha de parsing.
3. QUALIDADE DE DADOS: 1,059 processos de interesse foram ativamente ignorados por problemas de qualidade (outliers).

## --- Análise de Arquivos Concluída ---

### ==================== ANALISANDO CUSTOS PARA O MODELO: SABIAZINHO-3.0 ====================

[sabiazinho-3.0] Contando tokens em todos os 47204 processos...

  - Média de Tokens por Documento: 1,302
  - Total de Tokens (Entrada + Prompts + Schemas): 311,605,417

Calculando tokens de SAÍDA (dos JSONs gerados) para o modelo: sabiazinho-3.0...
  - Média de Tokens por Arquivo JSON de Saída: 2,483

### ==================== ANALISANDO CUSTOS PARA O MODELO: SABIA-3.0 ====================

[sabia-3.0] Contando tokens em todos os 47204 processos...
  - Média de Tokens por Documento: 1,302
[sabia-3.0] Contando tokens em todos os 47204 processos...
  - Média de Tokens por Documento: 1,302
  - Total de Tokens (Entrada + Prompts + Schemas): 311,605,417


Calculando tokens de SAÍDA (dos JSONs gerados) para o modelo: sabia-3.0...
Calculando tokens de SAÍDA (dos JSONs gerados) para o modelo: sabia-3.0...
  - Média de Tokens por Arquivo JSON de Saída: 2,483

### ==================== ANALISANDO CUSTOS PARA O MODELO: GEMINI-2.5-FLASH ====================

[Gemini] Contando tokens em 5000 processos e extrapolando para 47204...
  - Média de Tokens por Documento: 1,170
  - Total de Tokens (Entrada + Prompts + Schemas): 331,264,077

Calculando tokens de SAÍDA (dos JSONs gerados) para o modelo: gemini-2.5-flash...
  - Média de Tokens por Arquivo JSON de Saída: 2,431

### ==================== ANALISANDO CUSTOS PARA O MODELO: GEMINI-2.5-PRO ====================

[Gemini] Contando tokens em 5000 processos e extrapolando para 47204...
  - Média de Tokens por Documento: 1,170
  - Total de Tokens (Entrada + Prompts + Schemas): 331,264,077

Calculando tokens de SAÍDA (dos JSONs gerados) para o modelo: gemini-2.5-pro...
  - Média de Tokens por Arquivo JSON de Saída: 2,431


### ========================= RELATÓRIO DE CUSTOS COMPARATIVO =========================

--- PREVISÃO DE CUSTO PARA: SABIAZINHO-3.0 ---
  - Tokens de Entrada : 311,605,417
  - Tokens de Saída   : 117,226,886
  - Custo Entrada (IN): R$ 218.12
  - Custo Saída (OUT) : R$ 246.18
  - CUSTO TOTAL       : R$ 464.30

--- PREVISÃO DE CUSTO PARA: SABIA-3.0 ---
  - Tokens de Entrada : 311,605,417
  - Tokens de Saída   : 117,226,886
  - Custo Entrada (IN): R$ 1,090.62
  - Custo Saída (OUT) : R$ 820.59
  - CUSTO TOTAL       : R$ 1,911.21

--- PREVISÃO DE CUSTO PARA: GEMINI-2.5-FLASH ---
  - Tokens de Entrada : 331,264,077
  - Tokens de Saída   : 114,737,347
  - Custo Entrada (IN): R$ 546.59
  - Custo Saída (OUT) : R$ 1,577.64
  - CUSTO TOTAL       : R$ 2,124.22

--- PREVISÃO DE CUSTO PARA: GEMINI-2.5-PRO ---
  - Tokens de Entrada : 331,264,077
  - Tokens de Saída   : 114,737,347
  - Custo Entrada (IN): R$ 2,277.44
  - Custo Saída (OUT) : R$ 6,310.55
  - CUSTO TOTAL       : R$ 8,587.99