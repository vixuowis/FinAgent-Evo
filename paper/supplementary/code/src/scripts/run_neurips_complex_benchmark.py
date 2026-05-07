import os
import sys

root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if root not in sys.path:
    sys.path.insert(0, root)

import asyncio

from src.evaluation.complex_runner import main


if __name__ == "__main__":
    asyncio.run(main())
