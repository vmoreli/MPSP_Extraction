# MPSP Extraction

Pipeline de extração estruturada de informações a partir de **promoções de arquivamento** de inquéritos policiais do Ministério Público do Estado de São Paulo (MPSP).

Utiliza grafos LangGraph com modelos de linguagem (LLM) — Sabiazinho, Sabiá (Maritaca AI) e Gemini (Google) — para transformar documentos jurídicos em texto livre em registros JSON estruturados, com validação via schemas Pydantic.

---

## Sumário

- [Visão geral](#visão-geral)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Pipeline de extração](#pipeline-de-extração)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Como usar](#como-usar)
- [Formato da saída](#formato-da-saída)
- [Dataset](#dataset)
- [Experimentos](#experimentos)
- [Estimativas de custo](#estimativas-de-custo)
- [Limitações éticas e legais](#limitações-éticas-e-legais)
- [Licença](#licença)

---

## Visão geral

O pipeline recebe documentos jurídicos (`.txt`) de promoções de arquivamento e extrai, por meio de LLMs, as seguintes informações:

- **Classificação do crime** (Homicídio, Latrocínio, Morte natural)
- **Pessoas envolvidas** com seus papéis (vítima, suspeito, testemunha)
- **Detalhes do inquérito** (local, arma, data, delegacia, razão de arquivamento, etc.)
- **Informações individuais** de cada pessoa (sexo, cor, profissão, antecedentes, etc.)

O processamento é feito em paralelo, suportando dezenas de milhares de processos.

---

## Estrutura do repositório

```
mpsp-extraction/
│
├── extraction_pipeline/        # Código principal do pipeline
│   ├── config.py               # Caminhos, modelo padrão e tabela de preços
│   ├── main.py                 # Ponto de entrada: run_extraction_pipeline()
│   ├── graphs/
│   │   └── extract_data.py     # Definição do grafo LangGraph
│   ├── nodes/
│   │   └── extract_data_nodes.py  # Nós do grafo (funções de extração)
│   ├── prompts/
│   │   └── prompts.py          # Prompts enviados ao LLM
│   ├── schemas/
│   │   ├── extract_data_schemas.py  # Schemas Pydantic de saída
│   │   └── eval_schemas.py          # Schema para avaliação semântica
│   ├── services/
│   │   ├── llm_services.py     # Chamadas aos LLMs (Maritaca e Gemini) + contagem de tokens
│   │   └── loader_service.py   # Carregamento e filtragem de processos do disco
│   └── scripts/
│       ├── count_valid_processes.py  # Análise do funil de dados e estimativa de custo
│       └── visualize_graph.py        # Gera visualização do grafo (grafo.mmd / grafo.png)
│
├── experiments/                # Variantes experimentais do pipeline
│   ├── build_graphs.py
│   ├── prompts_variants.py
│   ├── run_variants.py
│   ├── schemas_variants.py
│   ├── utils.py
│   ├── README.md
│   └── aux/
│       ├── aggregate_variant.py
│       ├── eval_extraction_variants.py
│       └── generate_plots_variants.py
│
├── docs/
│   ├── dicionario_de_dados.md  # Descrição detalhada de todos os campos
│   ├── dataset.md              # Cobertura, granularidade, estatísticas e limitações
│   └── assets/
│       ├── pipeline_graph.png  # Visualização do grafo de extração
│       └── pipeline_graph.mmd  # Fonte Mermaid do grafo
│
├── examples/
│   └── registro_exemplo.json   # Exemplo de registro de saída
│
├── data/                       # Não versionado — criado localmente
│   ├── scraping/
│   │   └── attachments/        # Documentos .txt por processo (entrada do pipeline)
│   └── filters/                # JSONs de inclusão/exclusão de processos
│
├── preprocess_json_gt.py        # Pré-processa JSONs de ground truth para avaliação
├── validate_gt_against_schema.py # Valida JSONs de saída contra o schema
├── requirements.txt
├── .env.example
├── .gitignore
└── LICENSE
```

---

## Pipeline de extração

O pipeline é implementado como um grafo dirigido com LangGraph. Cada nó chama o LLM com um prompt específico e retorna a próxima etapa a executar (roteamento condicional).

```
START
  │
  ▼
[mapear envolvidos e classificar crime]
  │
  ├─ Morte natural ──────────────────────────► END
  │
  ▼
[extrair informações gerais do inquérito]
  │
  ├─ se há vítimas ──────► [extrair vítimas]
  │                              │
  ├─ se há suspeitos ────────────┤──► [extrair suspeitos]
  │                              │           │
  └─ se há testemunhas ──────────┤───────────┤──► [extrair testemunhas]
                                 │           │           │
                                 └───────────┴───────────┴──► END
```

Visualização completa em `docs/assets/pipeline_graph.png`.

---

## Instalação

### Pré-requisitos

- Python 3.10+
- Chave de API da [Maritaca AI](https://maritaca.ai) e/ou conta Google com acesso ao [Gemini API](https://ai.google.dev)

### Passos

```bash
# 1. Clone o repositório
git clone https://github.com/<seu-usuario>/mpsp-extraction.git
cd mpsp-extraction

# 2. Crie e ative um ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows

# 3. Instale as dependências
pip install -r requirements.txt
```

---

## Configuração

```bash
# Copie o template de variáveis de ambiente
cp .env.example .env

# Edite o .env com suas chaves
nano .env   # ou qualquer editor de sua preferência
```

O arquivo `.env` deve conter:

```
MARITACA_API_KEY=sua_chave_maritaca
GOOGLE_API_KEY=sua_chave_google   # opcional, se usar Gemini
```

### Estrutura de dados esperada

O pipeline espera que os documentos estejam organizados da seguinte forma:

```
data/scraping/attachments/
└── <prefixo_7_dígitos>/
    └── <NumMP>/
        └── texto_processo.txt
```

Arquivos de filtro (inclusão/exclusão de processos) devem estar em `data/filters/`.

---

## Como usar

### Execução padrão (todos os processos filtrados)

```python
from extraction_pipeline.main import run_extraction_pipeline

run_extraction_pipeline()
```

### Execução em modo de avaliação (subconjunto específico)

```python
run_extraction_pipeline(
    eval_mode=True,
    eval_path="ids_eval.json"   # JSON com lista de NumMPs a processar
)
```

### Parâmetros principais de `run_extraction_pipeline`

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `attachments_dir` | str | `data/scraping/attachments` | Diretório raiz dos processos |
| `output_dir` | str | `output` | Diretório de saída |
| `max_processes` | int \| None | `None` (todos) | Limita o número de processos |
| `model` | str | `"gemini-2.5-pro"` | Modelo LLM a usar |
| `random_seed` | int \| None | `42` | Semente para embaralhamento |
| `exclusion_file` | list | filtros padrão | JSONs com processos a excluir |
| `inclusion_file` | list | filtros padrão | JSONs com processos a incluir |
| `eval_mode` | bool | `False` | Ativa modo de avaliação |
| `eval_path` | str \| None | `None` | Caminho para o JSON de IDs de avaliação |

### Trocar o modelo

Edite `extraction_pipeline/config.py`:

```python
MODEL = "sabiazinho-3"   # ou "sabia-3.0", "gemini-2.5-flash", "gemini-2.5-pro"
```

### Validar JSONs de saída

```bash
python validate_gt_against_schema.py --input output/run_2024-01-01_12-00-00/results_gemini-2.5-pro.json
```

---

## Formato da saída

O pipeline gera um arquivo JSON em `output/run_<timestamp>/results_<modelo>.json`:

```json
{
  "13000000001234567": {
    "status": "success",
    "result": {
      "resumo_processo": { ... },
      "inquerito": { ... },
      "vitimas": { ... },
      "suspeitos": { ... },
      "testemunhas": { ... }
    }
  },
  "13000000009876543": {
    "status": "error",
    "message": "descrição do erro"
  }
}
```

Consulte `examples/registro_exemplo.json` para um exemplo completo de um registro com `status: success`.

Para a descrição detalhada de todos os campos, consulte `docs/dicionario_de_dados.md`.

---

## Dataset

Para informações completas sobre cobertura temporal, granularidade, estatísticas descritivas, taxa de valores ausentes e limitações, consulte `docs/dataset.md`.

**Resumo:**

| Métrica | Valor |
|---|---|
| Processos aptos para extração | ~47.204 |
| Cobertura geográfica | Estado de São Paulo — SP, Brasil |
| Tipos de crime | Homicídio, Latrocínio, Mortes investigadas |
| Unidade de análise | Inquérito policial arquivado |

---

## Experimentos

A pasta `experiments/` contém variantes do pipeline usadas em pesquisa, com diferentes topologias de grafo e prompts. Consulte `experiments/README.md` para instruções de uso.

---

## Estimativas de custo

Custo estimado para processar os ~47.204 processos aptos (junho/2025, dólar a R$ 5,50):

| Modelo | Custo total estimado |
|---|---|
| Sabiazinho-3 | R$ 464 |
| Sabiá-3.0 | R$ 1.911 |
| Gemini 2.5 Flash | R$ 2.124 |
| Gemini 2.5 Pro | R$ 8.588 |

Para regenerar estas estimativas com os dados atuais:

```bash
python -m extraction_pipeline.scripts.count_valid_processes
```

---

## Limitações éticas e legais

Este pipeline processa documentos contendo dados pessoais sensíveis (nomes, antecedentes, dados de saúde implícitos). O uso dos dados extraídos deve respeitar:

- A **LGPD (Lei nº 13.709/2018)**, em especial para dados de pessoas físicas identificáveis
- A **presunção de inocência** — suspeitos são investigados, não condenados
- A finalidade de **interesse público legítimo** (pesquisa científica, análise de segurança pública)

Consulte o arquivo `LICENSE` e `docs/dataset.md` para os termos completos.

---

## Licença

Código-fonte distribuído sob **MIT License**.

Os dados extraídos derivam de documentos públicos do MPSP (LAI) e seu uso deve respeitar a LGPD. Ver `LICENSE` para os termos completos.
