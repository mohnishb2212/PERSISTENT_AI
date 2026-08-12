from .agent import VisionAgent


def main():

    image_path = input("Enter image path: ")

    print()

    print("=" * 60)

    print("Running Vision Agent")

    print("=" * 60)

    print()

    agent = VisionAgent()

    result = agent.invoke(image_path)

    print()

    print("=" * 60)

    print("Vision Agent Completed")

    print("=" * 60)

    print()

    print("Output JSON")

    print(result["output_file"])


if __name__ == "__main__":

    main()