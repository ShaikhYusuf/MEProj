# codegen/protocols.py
from pathlib import Path
from src.design.objects import Object, ObjectModel

HEADER = '''"""GENERATED. Do not edit. Source: design/objects.py."""
from __future__ import annotations
from typing import Protocol, runtime_checkable
from datetime import datetime
from uuid import UUID
from app.models import *  # noqa: F401,F403 — generated SQLModel entities


'''

def render_object(o: Object) -> str:
    lines = [f'@runtime_checkable', f'class {o.protocol_name}(Protocol):']
    lines.append(f'    """{o.responsibility}"""')
    if not o.methods:
        lines.append("    ...")
    for m in o.methods:
        for sid in m.serves_steps:
            lines.append(f"    # @traces {sid}")
        params = ", ".join(
            f"{p.name}: {p.type}" + (" = ..." if p.optional else "")
            for p in m.params
        )
        arg_list = f"self, {params}" if params else "self"
        lines.append(f"    def {m.name}({arg_list}) -> {m.returns}: ...")
    return "\n".join(lines) + "\n"


def generate_protocols(om: ObjectModel, out_dir: Path = Path("app/contracts")) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for o in om.objects:
        path = out_dir / f"{o.name.lower()}.py"
        path.write_text(HEADER + render_object(o))
    # Bundle import file
    imports = "\n".join(f"from .{o.name.lower()} import {o.protocol_name}" for o in om.objects)
    __all__ = "[" + ", ".join(f'"{o.protocol_name}"' for o in om.objects) + "]"
    (out_dir / "__init__.py").write_text(imports + "\n\n__all__ = " + __all__ + "\n")