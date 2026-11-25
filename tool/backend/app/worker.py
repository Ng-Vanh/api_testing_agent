"""M0 storage readiness command; job execution is implemented in T10."""

import argparse

from langgraph.checkpoint.sqlite import SqliteSaver

from app.config import DATA_DIR
from app.storage import Store


def main():
    parser = argparse.ArgumentParser(description="Check worker storage readiness (M0)")
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    Store(DATA_DIR)
    with SqliteSaver.from_conn_string(str(DATA_DIR / "checkpoints.sqlite")) as saver:
        saver.setup()
    print(f"Worker storage ready: {DATA_DIR}")


if __name__ == "__main__":
    main()
