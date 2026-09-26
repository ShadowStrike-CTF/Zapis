# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""python -m zapis — thin launcher."""
import os
import sys

# Windowed exe: stdout/stderr are None and uvicorn's isatty() check crashes.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from zapis.main import main  # noqa: E402

main()
