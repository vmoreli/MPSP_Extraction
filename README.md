# MPSP Extraction

Pipeline de extração de informações estruturadas de inquéritos policiais do MPSP usando LLMs (Gemini e Sabiazinho/Maritaca) com LangGraph.

## Estrutura do repositório

```
MPSP_Extraction/
├── pipeline/               # Pipeline principal de extração
│   ├── config.py           # Configurações globais (modelo, preços, paths)
│   ├── main.py             # Ponto de entrada — executa o pipeline em paralelo
│   ├── graphs/             # Definição do grafo LangGraph
│   ├── nodes/              # Nós do grafo (lógica de extração por entidade)
│   ├── schemas/            # Schemas Pydantic (entidades e validações)
│   └── services/           # Clientes LLM e loader de processos
│
├── prompts/                # Fonte única de todos os prompts
│   ├── base.py             # Prompts individuais (vítimas, suspeitos, etc.)
│   └── combined.py         # Prompts combinados (experimento de variantes)
│
├── experiments/            # Experimentos paralelos (não produção)
│   └── graph_variants/     # Variantes do grafo para comparação de estratégias
│
├── evaluation/             # Scripts de avaliação e análise de resultados
│   ├── eval_extraction.py  # Avaliação NER + campos vs ground truth
│   ├── generate_plots.py   # Geração de gráficos comparativos
│   ├── preprocess_gt.py    # Normalização do ground truth
│   ├── validate_schema.py  # Validação de JSONs contra o schema Pydantic
│   ├── count_valid_processes.py  # Análise do dataset e estimativa de custo
│   └── scripts/            # Scripts auxiliares (junta, junta_tokens, visualize_graph)
│
├── data/                   # Arquivos de configuração e IDs de avaliação
│   └── ids_eval.json
│
└── outputs/                # Saídas geradas (ignoradas pelo git)
```

## Configuração

1. Copie o arquivo `.env.example` para `.env` e preencha as chaves:

```
MARITACA_API_KEY=sua_chave_maritaca
GOOGLE_API_KEY=sua_chave_google
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

## Uso

### Rodar o pipeline de extração

```bash
python -m pipeline.main
```

### Rodar o pipeline no modo de avaliação (subset de IDs)

```python
from pipeline.main import run_extraction_pipeline
run_extraction_pipeline(eval_mode=True, eval_path="data/ids_eval.json")
```

### Rodar variantes do experimento (um arquivo)

```bash
python -m experiments.graph_variants.run_variants <arquivo.txt> <provider> <api_key>
```

**Provider**: `maritaca` ou `gemini`

### Rodar variantes em lote (Windows)

```bat
evaluation\scripts\run_variants_batch.bat <pasta_com_txts>
```

### Avaliar resultados

```bash
python -m evaluation.eval_extraction
```

### Gerar gráficos

```bash
python -m evaluation.generate_plots
```

## Correções aplicadas nesta versão

| # | Arquivo | Problema | Correção |
|---|---------|----------|----------|
| 1 | `evaluation/scripts/junta.py` | `normalize_people(..., "suspeitos")` — chave minúscula, mas o schema salva `"Suspeitos"` | Segundo arg corrigido para `"Suspeitos"` |
| 2 | `evaluation/scripts/junta.py` | `data.get("vitimas")` não encontrava resultados salvos com acento `"vítimas"` | Adicionado fallback `data.get("vitimas") or data.get("vítimas")` |
| 3 | `evaluation/eval_extraction.py` | Mesmo problema de lookup de chaves na avaliação | Lookup defensivo com fallback para ambas as grafias |
| 4 | `pipeline/services/llm_services.py` | `genai.Client()` sem `api_key` falhava silenciosamente se `GOOGLE_API_KEY` ausente | Inicialização defensiva com erro claro via `_require_client()` |
| 5 | `requirements.txt` | `dotenv` é nome errado do pacote; faltavam `maritalk` e `google-generativeai` | Corrigido para `python-dotenv`, adicionados pacotes faltantes |
| 6 | `.gitignore` | `*.json` ignorava todos os JSONs, causando perda de arquivos fonte | Substituído por paths explícitos de pastas de output |
| 7 | Prompts | Duplicados em `extraction_pipeline/prompts/` e `graph_variantes/prompts_variants.py` | Unificados em `prompts/base.py` e `prompts/combined.py` |
| 8 | Estrutura | Scripts de avaliação na raiz, `Auxiliares/` sem estrutura clara | Reorganizados em `evaluation/` e `evaluation/scripts/` |
