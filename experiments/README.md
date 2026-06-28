# Experimentos — Variantes de Grafo

Esta pasta contém variantes experimentais do pipeline principal, usadas para comparar diferentes estratégias de prompting, arquiteturas de grafo e modelos LLM.

## Estrutura

```
experiments/
├── build_graphs.py         # Constrói diferentes topologias de grafo
├── prompts_variants.py     # Prompts alternativos testados
├── run_variants.py         # Script para rodar uma variante em um arquivo .txt
├── schemas_variants.py     # Schemas de saída para variantes
├── utils.py                # Utilitários de avaliação e comparação
└── aux/
    ├── aggregate_variant.py         # Agrega resultados de múltiplas execuções
    ├── eval_extraction_variants.py  # Avalia extração contra ground truth
    └── generate_plots_variants.py   # Gera gráficos comparativos
```

## Como rodar uma variante em um único arquivo

```bash
# Da raiz do repositório
python -m experiments.run_variants "caminho/para/arquivo.txt"
```

## Como rodar em lote (vários arquivos)

```bash
# Edite o arquivo .bat com o caminho correto antes de executar (Windows)
experiments/aux/run_variants_batch.bat "caminho/para/pasta/com/txts"
```

## Diferenças em relação ao pipeline principal

| Aspecto | Pipeline principal | Experimentos |
|---|---|---|
| Localização | `extraction_pipeline/` | `experiments/` |
| Foco | Produção, escala | Pesquisa, comparação |
| Saída | JSON consolidado | Resultados por variante |
| Avaliação | Separada | Integrada via `aux/` |
