import os
from extraction_pipeline.graphs.extract_data import pipeline

if __name__ == "__main__":
    # Obtém o grafo
    graph = pipeline.get_graph(xray=True)

    # --- Salvar PNG ---
    png_bytes = graph.draw_mermaid_png(max_retries=5, retry_delay=2.0)
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    png_path = os.path.join(output_dir, "grafo.png")
    with open(png_path, "wb") as f:
        f.write(png_bytes)
    print(f"PNG salvo em: {png_path}")

    # --- Salvar Mermaid (.mmd) ---
    mermaid_str = graph.draw_mermaid()
    mmd_path = os.path.join(output_dir, "grafo.mmd")
    with open(mmd_path, "w", encoding="utf-8") as f:
        f.write(mermaid_str)
    print(f"Mermaid salvo em: {mmd_path}")
