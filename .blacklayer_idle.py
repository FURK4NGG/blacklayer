#!/usr/bin/env python3

import sys
import time

path = sys.argv[1]
delay = float(sys.argv[2])

try:
    with open(path, "r", encoding="utf-8") as f:
        last = float(f.read().strip())

    idle = time.time() - last

    print(f"{idle:.3f}")

except Exception:
    print("0")
