from pathlib import Path

from .agent import VisionAgent
from .graph import build_graph


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def save_graph_image():
    graph = build_graph()
    output_file = PROJECT_ROOT / "vision_agent_graph.png"
    png_data = graph.get_graph().draw_mermaid_png()

    with open(output_file, "wb") as f:
        f.write(png_data)

    print(f"Workflow graph saved as: {output_file.name}")


def main():
    try:
        save_graph_image()
    except Exception as exc:
        print(f"Warning: Could not generate graph image: {exc}")

    print("\n" + "=" * 70)
    print("VISION AGENT — DATABASE-BACKED BOM EXTRACTION")
    print("=" * 70)

    catalogue = input(
        "Enter catalogue name (e.g. Apollo Tractors): "
    ).strip()

    image_path = input("Enter image path: ").strip()

    if not catalogue:
        print("Error: Catalogue name cannot be empty.")
        return

    if not image_path:
        print("Error: Image path cannot be empty.")
        return

    print("\n" + "=" * 70)
    print("Running Vision Agent")
    print("=" * 70)

    try:
        agent = VisionAgent()
        result = agent.invoke(image_path, catalogue)

        print("\n" + "=" * 70)
        print("VISION AGENT COMPLETED")
        print("=" * 70)
        print(f"Status      : {result.get('status')}")
        print(f"Output file : {result.get('output_file')}")

        bom = result.get("bom")
        if bom:
            print(f"Assembly    : {bom.assembly}")
            print(f"Catalogue   : {bom.catalogue}")
            print(f"Total parts : {bom.total_parts}")

    except Exception as exc:
        print("\nVision Agent failed.")
        print(f"Error: {exc}")


if __name__ == "__main__":
    main()