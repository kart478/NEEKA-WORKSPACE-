import logging

from neeka import NEEKAEngine


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    engine = NEEKAEngine()
    print(f"NEEKA Work Engine v0.2 ready ({len(engine.get_events())} events loaded)")
    engine.close()


if __name__ == "__main__":
    main()