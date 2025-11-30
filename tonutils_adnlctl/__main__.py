from __future__ import annotations

from colorama import init as colorama_init

from .cli import main

if __name__ == "__main__":
    colorama_init()
    main()
