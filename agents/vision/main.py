from pathlib import Path

from .agent import VisionAgent
from .graph import build_graph


def save_graph_image():

    # Build graph only for visualization
    graph = build_graph()

    # Go from:
    # PERSISTENT_AI/agents/vision/main.py
    # to:
    # PERSISTENT_AI/
    root_dir = Path(__file__).resolve().parents[2]

    output_file = root_dir / "vision_agent_graph.png"

    png_data = graph.get_graph().draw_mermaid_png()

    with open(output_file, "wb") as f:
        f.write(png_data)

    print(
        f"Workflow graph saved as: {output_file.name}"
    )


def main():

    # -------------------------------------------------
    # Generate workflow graph
    # -------------------------------------------------

    try:
        save_graph_image()

    except Exception as e:

        print(
            f"Warning: Could not generate graph image: {e}"
        )

    # -------------------------------------------------
    # Get image
    # -------------------------------------------------

    image_path = input(
        "Enter image path: "
    ).strip()

    if not image_path:

        print(
            "Error: Image path cannot be empty."
        )

        return

    print()

    print("=" * 60)
    print("Running Vision Agent")
    print("=" * 60)

    print()

    # -------------------------------------------------
    # Initialize Vision Agent
    # -------------------------------------------------

    agent = VisionAgent()

    # -------------------------------------------------
    # Run Vision Agent
    # -------------------------------------------------

    result = agent.invoke(
        image_path
    )

    # -------------------------------------------------
    # Display result
    # -------------------------------------------------

    print()

    print("=" * 60)
    print("Vision Agent Completed")
    print("=" * 60)

    print()

    print("Output JSON")

    print(
        result["output_file"]
    )


if __name__ == "__main__":
    main()