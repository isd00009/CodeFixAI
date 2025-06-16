import difflib
from typing import List

def generar_diff(original: str, corregido: str) -> List[str]:
    orig_lines = original.splitlines(keepends=True)
    corr_lines = corregido.splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_lines,
        corr_lines,
        fromfile="Original",
        tofile="Corregido",
        lineterm=""
    )
    return list(diff)
