import pathlib as pl

DATA_DIR = pl.Path("data")
SCRAPING_DIR = DATA_DIR / "scraping"
ATTACHMENTS_DIR = SCRAPING_DIR / "attachments"
PROCEDIMENTOS_DIR = SCRAPING_DIR / "csv" / "procedimentos.csv"
EDA_DIR = DATA_DIR / "eda"
LLM_DIR = DATA_DIR / "llm"
FILTERS_DIR = DATA_DIR / "filters"
OUTPUT_DIR = "output"
MODEL="sabiazinho-3.0"
MAX_PROCESSES=None
PRECOS = {
    "sabiazinho-3.0": {
        "in": 0.7,
        "out": 2.1
    },
    "sabia-3.0": {
        "in": 3.5,
        "out": 7.0
    }
}
