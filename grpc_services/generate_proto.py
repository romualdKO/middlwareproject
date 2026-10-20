"""Génère les stubs Python protobuf avec des imports compatibles au package."""
from pathlib import Path
import sys

from grpc_tools import protoc

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "grpc_services" / "generated"


def main():
    resultat = protoc.main([
        "grpc_tools.protoc",
        f"-I{ROOT / 'proto'}",
        f"--python_out={OUTPUT}",
        f"--grpc_python_out={OUTPUT}",
        str(ROOT / "proto" / "pharmacie.proto"),
        str(ROOT / "proto" / "radiologie.proto"),
    ])
    if resultat != 0:
        raise SystemExit(resultat)
    for nom in ("pharmacie", "radiologie"):
        chemin = OUTPUT / f"{nom}_pb2_grpc.py"
        contenu = chemin.read_text(encoding="utf-8")
        contenu = contenu.replace(f"import {nom}_pb2 as ", f"from . import {nom}_pb2 as ")
        chemin.write_text(contenu, encoding="utf-8")


if __name__ == "__main__":
    main()
