"""
Script de normalização de JSONs de inquéritos policiais

CONVENÇÕES E TRATAMENTOS APLICADOS:
-----------------------------------
1. Exclusão de campos com valor NaN.
2. Campos como "vitimas[0].nome" são agrupados em listas de dicionários.
3. Renomeações de campos:
   - "antecedentes" → "antecedentes_criminais"
   - "arma" → "arma_utilizada"
   - "pericia" → "pericia_realizada"
   - "autores" → "suspeitos_investigados"
4. Adição de campo "é_policial" em pessoas (default: False).
5. Nova estrutura inicial:
   "resumo_processo": {
       "pessoas_envolvidas": {
           "vitimas": [...],
           "suspeitos_investigados": [...],
           "testemunhas": [...]
       },
       "classificacao_crime": "Homicídio" | "Morte por causas naturais"
   }
6. Regra para classificação do crime:
   - Se "causa_juridica_da_morte" contém "causas naturais" (case-insensitive) → "Morte por causas naturais"
   - Caso contrário → "Homicídio"
7. Campos adicionados em "inquerito":
   - "resultado": "consumado" ou "tentado" (com base em "homicidio_consumado")
   - "é_feminicídio": False
   - "homicidio_consumado" é removido
8. Campos movidos do "inquerito" para a vítima (somente se há exatamente uma vítima):
   - "arma_da_vitima"
   - "causa_juridica_da_morte"
   - "relacao_vitima_autor"
   - Novos campos derivados:
       - "armada" (True se "arma_da_vitima" for informada)
       - "faleceu" (True se resultado == "consumado")
   Os inquéritos com 0 ou mais de 1 vítima são impressos no terminal e mantêm esses campos no inquérito.
9. Ordem consistente de chaves:
   - resumo_processo
   - vitimas
   - suspeitos_investigados
   - testemunhas
   - inquerito
"""

import json
import math
from collections import defaultdict, OrderedDict

def normalize_inquerito_json(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    normalized = {}

    for numMP, values in data.items():
        vitimas, suspeitos, testemunhas = defaultdict(dict), defaultdict(dict), defaultdict(dict)
        inquerito = {}

        # --- Processa as chaves ---
        for key, value in values.items():
            if value == "NaN" or (isinstance(value, float) and math.isnan(value)):
                continue

            if key.startswith("vitimas["):
                idx = int(key.split("[")[1].split("]")[0])
                subkey = key.split("].")[1]
                if subkey == "antecedentes":
                    subkey = "antecedentes_criminais"
                vitimas[idx][subkey] = value

            elif key.startswith("autores["):
                idx = int(key.split("[")[1].split("]")[0])
                subkey = key.split("].")[1]
                if subkey == "antecedentes":
                    subkey = "antecedentes_criminais"
                suspeitos[idx][subkey] = value

            elif key.startswith("testemunhas["):
                idx = int(key.split("[")[1].split("]")[0])
                subkey = key.split("].")[1]
                if subkey == "antecedentes":
                    subkey = "antecedentes_criminais"
                testemunhas[idx][subkey] = value

            elif key.startswith("inquerito."):
                subkey = key.split(".", 1)[1]
                if subkey == "arma":
                    subkey = "arma_utilizada"
                elif subkey == "pericia":
                    subkey = "pericia_realizada"
                inquerito[subkey] = value

        # --- Converte dicionários em listas ---
        vitimas_list = list(vitimas.values())
        suspeitos_list = list(suspeitos.values())
        testemunhas_list = list(testemunhas.values())

        # --- Trata autores/suspeitos ---
        if isinstance(suspeitos_list, str) and suspeitos_list == "{'autores': None}":
            suspeitos_list = None

        # --- Adiciona "é_policial" ---
        for pessoa in vitimas_list + testemunhas_list + (suspeitos_list or []):
            pessoa["é_policial"] = pessoa.get("corporacao_policial", "").lower() != "não é policial"

        # --- Trata classificação do crime ---
        causa_morte = str(inquerito.get("causa_juridica_da_morte", "")).lower()
        if "causas naturais" in causa_morte:
            classificacao_crime = "Morte por causas naturais"
        else:
            classificacao_crime = "Homicídio"

        # --- Trata resultado e é_feminicídio ---
        homicidio_consumado = inquerito.pop("homicidio_consumado", False)
        inquerito["resultado"] = "consumado" if homicidio_consumado else "tentado"
        inquerito["é_feminicídio"] = False

        # --- Campos movidos para vítima (somente se há 1 vítima) ---
        if len(vitimas_list) == 1:
            v = vitimas_list[0]
            v["arma_da_vitima"] = inquerito.pop("arma_da_vitima", None)
            v["causa_jurídica_da_morte"] = inquerito.pop("causa_juridica_da_morte", None)
            v["relacao_vitima_autor"] = inquerito.pop("relacao_vitima_autor", None)
            v["armada"] = bool(v.get("arma_da_vitima") and str(v["arma_da_vitima"]).strip().lower() != "não informado")
            v["faleceu"] = inquerito["resultado"] == "consumado"
        else:
            # Printa inquéritos problemáticos
            print(f"Inquérito {numMP}: número inválido de vítimas ({len(vitimas_list)})")

        # --- Cria resumo_processo ---
        resumo_processo = {
            "pessoas_envolvidas": {
                "vitimas": [v.get("nome") for v in vitimas_list if v.get("nome")],
                "suspeitos_investigados": [s.get("nome") for s in (suspeitos_list or []) if s.get("nome")],
                "testemunhas": [t.get("nome") for t in testemunhas_list if t.get("nome")],
            },
            "classificacao_crime": classificacao_crime,
        }

        # --- Monta estrutura final (ordem consistente) ---
        final_obj = OrderedDict()
        final_obj["resumo_processo"] = resumo_processo
        final_obj["vitimas"] = vitimas_list
        final_obj["suspeitos_investigados"] = suspeitos_list
        final_obj["testemunhas"] = testemunhas_list
        final_obj["inquerito"] = inquerito

        normalized[numMP] = final_obj

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=4)

    print(f"JSON normalizado salvo em: {output_path}")


if __name__ == "__main__":
    normalize_inquerito_json("resultado_revisao.json", "output_normalizado.json")
