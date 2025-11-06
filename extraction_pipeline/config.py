import pathlib as pl

DATA_DIR = pl.Path("data")
SCRAPING_DIR = DATA_DIR / "scraping"
ATTACHMENTS_DIR = SCRAPING_DIR / "attachments"
PROCEDIMENTOS_DIR = SCRAPING_DIR / "csv" / "procedimentos.csv"
EDA_DIR = DATA_DIR / "eda"
LLM_DIR = DATA_DIR / "llm"
FILTERS_DIR = DATA_DIR / "filters"
OUTPUT_DIR = "output"
MAX_PROCESSES=None

MODEL="sabiazinho-3"
PRECOS = {  # preços em reais por milhão de tokens
    "sabiazinho-3": {
        "in": 0.7,
        "out": 2.1
    },
    "sabia-3.0": {
        "in": 3.5,
        "out": 7.0
    },
    "sabia-3.1":{
        "in": 5,
        "out": 10
    },
    "gemini-2.5-pro": { # considerei dolar a 5.50
        "in": 6.875,
        "out": 55.0
    },
    "gemini-2.5-flash": {
        "in": 1.65,
        "out": 13.75
    }
}
