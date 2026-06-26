# evaluation/

Pasta com todos os scripts de avaliação, análise e pré-processamento do projeto MPSP Extraction. Cada arquivo tem um papel bem definido no fluxo que vai da execução do pipeline até a geração de métricas e gráficos.

---

## Fluxo geral

```
Ground truth bruto (planilha)
        ↓
   preprocess_gt.py          ← normaliza e converte para JSON compatível com o pipeline
        ↓
   validate_schema.py        ← valida o JSON normalizado contra os schemas Pydantic
        ↓
Pipeline de extração roda    ← (em pipeline/main.py ou experiments/graph_variants/)
        ↓
   scripts/junta.py          ← agrega resultados das variantes no formato do eval
        ↓
   eval_extraction.py        ← compara predições vs. ground truth, gera métricas
        ↓
   generate_plots.py         ← lê os relatórios e gera gráficos comparativos
```

---

## Arquivos raiz

### `eval_extraction.py`

Script principal de avaliação. Compara os JSONs gerados pelo pipeline com o ground truth anotado manualmente e produz dois arquivos por execução:

- `metricas_brutas.csv` — uma linha por campo avaliado, com `process_id`, `context` (ex: `vítimas[0]`), `field`, valor predito, valor esperado, `result` (TP/FP/FN/etc.) e `score`.
- `relatorio_final_analitico.json` — métricas agregadas de precisão, recall e F1 por campo e por entidade (vítimas, suspeitos, testemunhas, inquérito).

**Como funciona a comparação:**
- Campos categóricos com vocabulário controlado (`classificacao_crime`, `natureza_da_autoria`, `resultado`) são comparados por igualdade exata após normalização.
- Campos textuais livres (nomes, razão de arquivamento, etc.) são comparados por similaridade semântica com o modelo `intfloat/multilingual-e5-large` via `sentence-transformers`. O limiar padrão é `0.8`.
- Campos booleanos e numéricos são comparados por igualdade direta.
- O matching entre listas de entidades (ex: múltiplas vítimas) é feito por nome, com fallback para melhor similaridade disponível.

**Correções aplicadas:**
- Lookup defensivo para `vítimas` (com/sem acento) e `Suspeitos` (maiúsculo), garantindo compatibilidade com resultados vindos tanto do pipeline principal quanto do `junta.py`.

---

### `generate_plots.py`

Lê os relatórios gerados pelo `eval_extraction.py` e produz visualizações comparativas entre modelos e arquiteturas. Espera encontrar pastas no padrão `{modo}_{modelo}/` (ex: `st_5_gemini-2.5-flash/`) com os arquivos `relatorio_final_analitico.json` e `metricas_brutas.csv` dentro.

**Gráficos gerados:**
- Métricas NER (precisão, recall, F1) por entidade e por modelo.
- Distribuição de erros por tipo (FP, FN, campo errado, etc.).
- Acurácia por campo do inquérito, permitindo identificar quais campos cada modelo acerta mais.

**Configuração:** edite as variáveis `MODOS`, `MODELOS` e `BASE_DIR` no topo do arquivo antes de rodar.

---

### `preprocess_gt.py`

Normaliza o ground truth bruto (originalmente em planilha/CSV) para o formato JSON compatível com o schema Pydantic do pipeline. Aplica uma série de transformações documentadas no cabeçalho do arquivo:

- Converte campos planos (`vitimas[0].nome`, `vitimas[0].sexo`, ...) em listas de objetos.
- Renomeia campos legados (`antecedentes` → `antecedentes_criminais`, `arma` → `arma_utilizada`, etc.).
- Infere `é_policial` com base no campo `corporacao_policial`.
- Classifica o crime como `"Homicídio"` ou `"Morte por causas naturais"` com base em `causa_juridica_da_morte`.
- Deriva os campos `armada`, `faleceu` e `resultado` a partir dos dados brutos.
- Move campos da vítima que estavam no inquérito (quando há exatamente uma vítima).

**Uso:**
```bash
python -m evaluation.preprocess_gt --input planilha.csv --output data/groundtruth.json
```

---

### `validate_schema.py`

Valida um JSON de saída (do pipeline ou do ground truth normalizado) contra os schemas Pydantic definidos em `pipeline/schemas/extract_data_schemas.py`. Útil para detectar inconsistências antes de rodar o eval.

Tenta instanciar `InqueritoTotal` para cada processo e reporta os erros de validação com o `process_id` correspondente. Aceita o caminho do JSON como argumento de linha de comando.

**Uso:**
```bash
python -m evaluation.validate_schema caminho/para/resultado.json
```

---

### `count_valid_processes.py`

Script utilitário para análise do corpus e estimativa de custo. Para um diretório de processos (`.txt`), calcula:

- Quantidade total de processos válidos (após filtros de inclusão/exclusão).
- Distribuição de tokens por processo e por prompt (usando a API da Maritaca para contagem exata e a API do Google para estimativa com Gemini).
- Estimativa de custo total em R$ para rodar o pipeline completo, com base na tabela de preços de `pipeline/config.py`.

> Requer `MARITACA_API_KEY` e `GOOGLE_API_KEY` no `.env`. Os textos dos processos são enviados às APIs apenas para contagem de tokens, não para extração.

---

## scripts/

### `scripts/junta.py`

Agrega os resultados individuais gerados pelo pipeline de variantes (`experiments/graph_variants/`) no formato esperado pelo `eval_extraction.py`. Cada variante gera um JSON por processo — este script os consolida em um único JSON por variante com a estrutura `{process_id: {result: {...}}}`.

**Correções aplicadas:**
- Aceita `vitimas` com ou sem acento como chave de entrada (`data.get("vitimas") or data.get("vítimas")`).
- Segundo argumento de `normalize_people` corrigido para `"Suspeitos"` (maiúsculo), alinhado com o campo do schema Pydantic.

**Uso:**
```bash
python evaluation/scripts/junta.py
```

Gera os arquivos em `extraction_results/` no formato pronto para o `eval_extraction.py`.

---

### `scripts/junta_tokens.py`

Consolida os JSONs de estatísticas de tokens gerados durante execuções do pipeline. Para cada processo, agrega o total de tokens e o breakdown por prompt (`prompt_mapeamento`, `prompt_vitimas`, etc.) em um único CSV (`consolidado_tokens.csv`).

Útil para análise de custo por nó do grafo e para identificar quais prompts consomem mais tokens.

**Uso:**
```bash
python evaluation/scripts/junta_tokens.py <diretorio_com_jsons_de_tokens>
```

---

### `scripts/visualize_graph.py`

Renderiza o grafo LangGraph do pipeline principal (`pipeline/graphs/extract_data.py`) e salva em dois formatos em `outputs/`:

- `grafo.png` — imagem renderizada via Mermaid.
- `grafo.mmd` — código Mermaid para edição ou inclusão em documentação.

> Como os nós usam `Command(goto=...)` para roteamento dinâmico, as arestas não aparecem no diagrama gerado — comportamento esperado do LangGraph com fluxo baseado em comandos.

**Uso:**
```bash
python -m evaluation.scripts.visualize_graph
```

---

### `scripts/run_variants_batch.bat`

Script Windows (`.bat`) para rodar o pipeline de variantes em lote sobre uma pasta de arquivos `.txt`. Itera sobre os processos e chama `experiments/graph_variants/run_variants.py` para cada um.

Útil para reproduzir os experimentos de arquitetura em ambiente Windows sem precisar escrever um loop manualmente.

**Uso:**
```bat
evaluation\scripts\run_variants_batch.bat <pasta_com_txts>
```
