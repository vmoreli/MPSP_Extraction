# Dicionário de Dados — MPSP Extraction

Este documento descreve todos os campos presentes no JSON de saída gerado pelo pipeline.
Cada processo extraído produz um objeto JSON com a estrutura descrita abaixo.

---

## Estrutura de alto nível

```
{
  "resumo_processo":  { ... },   # Classificação e lista de pessoas
  "inquerito":        { ... },   # Detalhes do inquérito policial
  "vítimas":          { ... },   # Dados individuais de cada vítima
  "suspeitos":        { ... },   # Dados individuais de cada suspeito
  "testemunhas":      { ... }    # Dados individuais de cada testemunha
}
```

---

## `resumo_processo`

| Campo | Tipo | Valores possíveis | Descrição |
|---|---|---|---|
| `classificacao_crime` | string (enum) | `"Homicídio"`, `"Latrocínio (roubo seguido de morte)"`, `"Morte por causas naturais"` | Classificação jurídica principal do fato |
| `pessoas_envolvidas.vitimas` | lista de strings | — | Nomes completos das vítimas identificadas |
| `pessoas_envolvidas.suspeitos_investigados` | lista de strings | — | Nomes completos dos suspeitos/investigados |
| `pessoas_envolvidas.testemunhas` | lista de strings | — | Nomes completos das testemunhas |

---

## `inquerito`

| Campo | Tipo | Valores possíveis | Descrição |
|---|---|---|---|
| `resultado` | string (enum) \| null | `"Consumado"`, `"Tentado"` | Se o crime foi consumado ou tentado. Null para mortes naturais |
| `é_feminicidio` | boolean | `true`, `false` | True apenas quando há qualificadora de feminicídio (só aplicável a homicídios) |
| `data_ocorrencia` | string \| null | Formato livre (ex: `"15/03/2024"`) | Data da ocorrência conforme o documento |
| `hora_ocorrencia` | string \| null | Formato livre (ex: `"22:30"`) | Hora da ocorrência |
| `data_registro` | string \| null | Formato livre | Data do registro do inquérito |
| `delegacia_registro` | string \| null | — | Nome ou sigla da delegacia que registrou a ocorrência |
| `tipo_de_local` | string \| null | — | Tipo do local (ex: `"Residência"`, `"Via pública"`, `"Estabelecimento comercial"`) |
| `local_detalhado` | string \| null | — | Descrição mais detalhada do local (ex: `"quarto"`, `"calçada"`) |
| `municipio` | string \| null | — | Município da ocorrência |
| `latitude` | float \| null | Coordenada WGS-84 | Latitude do local (quando disponível) |
| `longitude` | float \| null | Coordenada WGS-84 | Longitude do local (quando disponível) |
| `arma_utilizada` | string \| null | — | Arma empregada pelo autor (ex: `"revólver calibre 38"`, `"faca de cozinha"`) |
| `bem_roubado` | string \| null | — | Descrição do bem subtraído (preenchido apenas em latrocínios) |
| `natureza_da_autoria` | string (enum) \| null | `"Conhecida"`, `"Desconhecida"`, `"Não aplicável"` | Situação da autoria ao momento do arquivamento |
| `pericia_realizada` | boolean \| null | `true`, `false` | Se houve perícia no local ou em armas |
| `prisao_em_flagrante` | boolean \| null | `true`, `false` | Se houve prisão em flagrante |
| `razao_arquivamento` | string \| null | — | Trecho literal do documento que fundamenta o arquivamento |

---

## Campos comuns a `vítimas`, `suspeitos` e `testemunhas` (tipo `Pessoa`)

| Campo | Tipo | Descrição |
|---|---|---|
| `nome` | string \| null | Nome completo |
| `sexo` | string \| null | `"Masculino"` ou `"Feminino"` (inferido pelo nome quando não informado explicitamente) |
| `cor` | string \| null | Cor/raça conforme o documento |
| `idade` | string \| null | Idade ou faixa etária aproximada |
| `profissao` | string \| null | Profissão ou ocupação |
| `escolaridade` | string \| null | Nível de escolaridade |
| `nacionalidade` | string \| null | Nacionalidade |
| `antecedentes_criminais` | string \| null | Antecedentes criminais. Não inclui informações comportamentais (ex: uso de álcool) |
| `é_policial` | boolean | Se a pessoa é policial |
| `corporacao_policial` | string \| null | Corporação (preenchido apenas se `é_policial=true`) |
| `policial_em_servico` | boolean \| null | Se estava em serviço no momento (preenchido apenas se `é_policial=true`) |

---

## Campos exclusivos de `vítimas` (tipo `Vitima`, herda de `Pessoa`)

| Campo | Tipo | Descrição |
|---|---|---|
| `armada` | boolean | Se a vítima estava armada no momento da ocorrência |
| `arma_da_vítima` | string \| null | Arma portada pela vítima (preenchido apenas se `armada=true`) |
| `faleceu` | boolean | Se a vítima faleceu |
| `causa_juridica_da_morte` | string \| null | Tipificação da causa da morte (preenchido apenas se `faleceu=true`) |
| `relacao_vitima_autor` | string \| null | Relação entre a vítima e o autor (ex: `"Companheira"`, `"Desconhecido"`) |

---

## Notas sobre valores ausentes

- Campos `null` indicam que a informação não estava disponível no documento original.
- O modelo **nunca inventa** dados: campos não mencionados no texto são deixados `null`.
- Campos booleanos têm valor padrão `false` quando não há indicação contrária.
- Coordenadas geográficas (`latitude`, `longitude`) raramente aparecem nos documentos e tendem a ter alta taxa de `null`.

---

## Regras de negócio aplicadas pelo pipeline

1. `é_feminicidio` só pode ser `true` se `classificacao_crime == "Homicídio"`.
2. `bem_roubado` só é preenchido se `classificacao_crime == "Latrocínio"`.
3. `resultado` não é preenchido para `"Morte por causas naturais"`.
4. Latrocínios são sempre `resultado == "Consumado"` (pela definição jurídica).
5. Processos classificados como `"Morte por causas naturais"` não passam pelos nós de extração detalhada — apenas `resumo_processo` é preenchido.
