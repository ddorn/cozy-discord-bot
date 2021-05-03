import sys
from pathlib import Path

sys.path.append(str((Path(__file__).parent / "src").absolute()))

from src import start

if __name__ == "__main__":
    start()
