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
   - Critério:
       • Se "corporacao_policial" for "não é policial", "nao é policial", "nan", None, ou NaN → False
       • Caso contrário → True
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
   - "resultado": "Consumado" ou "Tentado" (com base em "homicio_consumado", tratando variações como "consumada", "tentada").
   - "é_feminicídio": False
   - "homicio_consumado" é removido (mantido com o erro de digitação propositalmente)
8. Campos movidos do "inquerito" para a vítima (somente se há exatamente uma vítima):
   - "arma_da_vitima"
   - "causa_juridica_da_morte"
   - "relacao_vitima_autor"
   - Novos campos derivados:
       - "armada" (True se "arma_da_vitima" for informada e não "não informado"/NaN/None)
       - "faleceu" (True se resultado == "Consumado")
   Os inquéritos com 0 ou mais de 1 vítima são impressos no terminal e mantêm esses campos no inquérito.
9. Ordem consistente de chaves:
   - resumo_processo
   - vitimas
   - suspeitos_investigados
   - testemunhas
   - inquerito
10. Normalização de grafia de campos:
    - "inquerito.natureza_da_autoria": Padronizado para "Conhecida", "Desconhecida" ou "Não aplicável" (tratando variações).
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

        # --- Adiciona "é_policial" com critérios claros ---
        def determinar_se_policial(valor):
            """Determina se uma pessoa é policial com base no campo 'corporacao_policial'."""
            if valor is None:
                return False
            if isinstance(valor, float) and math.isnan(valor):
                return False
            valor_str = str(valor).strip().lower()
            if valor_str in {"não é policial", "nao é policial", "nan", ""}:
                return False
            return True

        for pessoa in vitimas_list + testemunhas_list + (suspeitos_list or []):
            pessoa["é_policial"] = determinar_se_policial(pessoa.get("corporacao_policial"))
            if "idade" in pessoa:
                pessoa["idade"] = str(pessoa["idade"])

        # --- Trata classificação do crime ---
        causa_morte = str(inquerito.get("causa_juridica_da_morte", "")).lower()
        if "causas naturais" in causa_morte:
            classificacao_crime = "Morte por causas naturais"
        else:
            classificacao_crime = "Homicídio"

        # --- Trata resultado e é_feminicídio (Regra 7) ---
        homicidio_consumado_raw = inquerito.pop("homicio_consumado", False)  # mantido o typo intencional
        
        # Normaliza o valor lido (que pode ser bool, string, etc.)
        val_norm = str(homicidio_consumado_raw).strip().lower()

        # Determina se foi consumado
        is_consumado = False
        if val_norm in {"true", "consumado", "consumada"}:
            is_consumado = True
        # Se for "tentado", "tentada", "false", ou o default (False) -> is_consumado continua False.

        # Define o valor final com a grafia correta (Capitalized)
        inquerito["resultado"] = "Consumado" if is_consumado else "Tentado"
        inquerito["é_feminicídio"] = False

        # --- Função auxiliar: valor informado ---
        def valor_informado(valor):
            """Retorna True se o valor for válido (não informado, NaN ou None são considerados não informados)."""
            if valor is None:
                return False
            if isinstance(valor, float) and math.isnan(valor):
                return False
            valor_str = str(valor).strip().lower()
            return valor_str not in {"não informado", "nao informado", "nan", ""}

        # --- Campos movidos para vítima (1 vítima ou casos especiais) (Regra 8) ---
        casos_multiplas_vitimas_especiais = {
            "130239000004720132",
            "130244000006920139",
            "130248000033520210",
            "130309000088020125",
            "130278000067920157",
            "130388000020220144",
        }

        if len(vitimas_list) == 1 or numMP in casos_multiplas_vitimas_especiais:
            # Função para aplicar os campos do inquérito na vítima
            def aplicar_campos_vitima(v, sobrescrever_faleceu=None):
                v["arma_da_vitima"] = inquerito.get("arma_da_vitima")
                v["causa_juridica_da_morte"] = inquerito.get("causa_juridica_da_morte")
                v["relacao_vitima_autor"] = inquerito.get("relacao_vitima_autor")
                v["armada"] = valor_informado(v.get("arma_da_vitima"))
                if sobrescrever_faleceu is not None:
                    v["faleceu"] = sobrescrever_faleceu
                else:
                    # (Regra 8) Compara com o valor normalizado ("Consumado")
                    v["faleceu"] = inquerito["resultado"] == "Consumado"

            # --- Casos específicos ---
            if numMP in {"130239000004720132", "130244000006920139", "130248000033520210", "130309000088020125"}:
                for v in vitimas_list:
                    aplicar_campos_vitima(v)

            elif numMP == "130278000067920157":
                # Este caso específico já define como "Conhecida", o que está correto.
                inquerito["natureza_da_autoria"] = "Conhecida" 
                for v in vitimas_list:
                    nome = str(v.get("nome", "")).strip().lower()
                    if nome.startswith("josé"):
                        aplicar_campos_vitima(v, sobrescrever_faleceu=True)
                    elif nome.startswith("tabata"):
                        aplicar_campos_vitima(v, sobrescrever_faleceu=False)
                    else:
                        aplicar_campos_vitima(v)

            elif numMP == "130388000020220144":
                for v in vitimas_list:
                    nome = str(v.get("nome", "")).strip().lower()
                    if nome.startswith("robson"):
                        aplicar_campos_vitima(v, sobrescrever_faleceu=True)
                    elif nome.startswith("eric"):
                        aplicar_campos_vitima(v, sobrescrever_faleceu=False)
                    else:
                        aplicar_campos_vitima(v)

            else:
                # Caso padrão: 1 vítima
                v = vitimas_list[0]
                aplicar_campos_vitima(v)

            # Remover campos do inquérito que foram movidos
            for campo in ["arma_da_vitima", "causa_juridica_da_morte", "relacao_vitima_autor"]:
                inquerito.pop(campo, None)

            # Se faleceu = False, então causa_jurídica_da_morte deve ser vazio
            for v in vitimas_list:
                if v.get("faleceu") is False:
                    v["causa_juridica_da_morte"] = ""

        else:
            print(f"Inquérito {numMP}: número inválido de vítimas ({len(vitimas_list)})")

        # --- (Regra 10 Modificada) Normaliza 'natureza_da_autoria' ---
        natureza_raw = inquerito.get("natureza_da_autoria")
        
        # Define o default
        final_value = "Não aplicável" 

        if natureza_raw: # Somente processa se não for None
            val_norm = str(natureza_raw).strip().lower()
            
            if val_norm in {"conhecida", "conhecido"}:
                final_value = "Conhecida"
            elif val_norm in {"desconhecida", "desconhecido"}:
                final_value = "Desconhecida"
            # Se for "nan", "em investigação", ou qualquer outro valor, 
            # o valor "Não aplicável" definido no início será usado.

        inquerito["natureza_da_autoria"] = final_value

        # --- Cria resumo_processo (Regra 5) ---
        resumo_processo = {
            "pessoas_envolvidas": {
                "vitimas": [v.get("nome") for v in vitimas_list if v.get("nome")],
                "suspeitos_investigados": [s.get("nome") for s in (suspeitos_list or []) if s.get("nome")],
                "testemunhas": [t.get("nome") for t in testemunhas_list if t.get("nome")],
            },
            "classificacao_crime": classificacao_crime,
        }

        # --- Monta estrutura final (Regra 9) ---
        final_obj = OrderedDict()
        final_obj["resumo_processo"] = resumo_processo
        final_obj["vitimas"] = vitimas_list
        final_obj["suspeitos"] = suspeitos_list
        final_obj["testemunhas"] = testemunhas_list
        final_obj["inquerito"] = inquerito

        normalized[numMP] = final_obj

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=4)

    print(f"JSON normalizado salvo em: {output_path}")


if __name__ == "__main__":
    normalize_inquerito_json("resultado_revisao.json", "output_normalizado.json")