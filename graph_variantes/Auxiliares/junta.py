import json
from pathlib import Path

BASE_DIR = Path("results_variants/graphs")
OUTPUT_DIR = Path("extraction_results")
OUTPUT_DIR.mkdir(exist_ok=True)

variants = sorted([p for p in BASE_DIR.iterdir() if p.is_dir()])

if not variants:
    raise RuntimeError("Nenhuma variante encontrada em results_variants/graphs/")

print(f"Encontradas {len(variants)} variantes.")


def normalize_people(container, key):
    """
    Aceita dois formatos de entrada:

    1) lista direta
       ex: [{"nome": "..."}]

    2) dicionário contendo a lista na chave esperada
       ex: {"vitimas": [{...}]}
    """
    if isinstance(container, list):
        return container

    if isinstance(container, dict):
        value = container.get(key)
        return value if isinstance(value, list) else []

    return []


for variant_dir in variants:
    variant = variant_dir.name
    print(f"\nAgregando variante (formato compatível com eval): {variant}")

    aggregated = {}

    json_files = list(variant_dir.glob("*.json"))
    if not json_files:
        print(f"  [AVISO] Nenhum JSON encontrado em {variant}")
        continue

    for json_file in json_files:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        pid = json_file.stem

        aggregated[pid] = {
            "result": {
                "resumo_processo": data.get("resumo_processo", {}),
                "inquerito": data.get("inquerito", {}),
                "vítimas": {
                    "vitimas": normalize_people(data.get("vitimas"), "vitimas")
                },
                "suspeitos": {
                    "Suspeitos": normalize_people(data.get("suspeitos"), "suspeitos")
                },
                "testemunhas": {
                    "testemunhas": normalize_people(data.get("testemunhas"), "testemunhas")
                }
            }
        }

    out_path = OUTPUT_DIR / f"{variant}_results.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(aggregated, f, ensure_ascii=False, indent=2)

    print(f"  → Gerado: {out_path} ({len(aggregated)} processos)")

print("\nTodas as variantes foram agregadas no formato esperado pelo eval.")