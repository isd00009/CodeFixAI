import difflib
from typing import List


def generar_diff(original: str, corregido: str) -> List[str]:
    if not original.endswith("\n"):
        original += "\n"
    if not corregido.endswith("\n"):
        corregido += "\n"

    orig_lines = [line.rstrip() + "\n" for line in original.splitlines()]
    corr_lines = [line.rstrip() + "\n" for line in corregido.splitlines()]

    raw = difflib.unified_diff(
        orig_lines,
        corr_lines,
        fromfile="Original",
        tofile="Corregido",
        lineterm=""
    )

    orig_set = {l.rstrip("\n") for l in orig_lines}
    corr_set = {l.rstrip("\n") for l in corr_lines}

    filtered: List[str] = []
    for line in raw:
        if line.startswith("+") and not line.startswith("+++"):
            content = line[1:].rstrip("\n")
            # si ese contenido normalizado ya existía en el original, lo saltamos
            if content in orig_set:
                continue
        elif line.startswith("-") and not line.startswith("---"):
            content = line[1:].rstrip("\n")
            # si ese contenido normalizado ya existe en el corregido, lo saltamos
            if content in corr_set:
                continue
        filtered.append(line)

    return filtered
