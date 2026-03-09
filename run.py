#!/usr/bin/env python3
"""
run.py — Orquestador: retrieve → parse → stats

Uso:
    python3 run.py                  # ciclo completo
    python3 run.py --sin-retrieve   # solo parse + stats (ya tienes los .tcx)
    python3 run.py --dias 30        # retrieve solo últimos 30 días
    python3 run.py --forzar-todo    # re-descarga y re-importa todo
"""

import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime


def run(cmd: list[str], desc: str) -> bool:
    print(f"\n{'─'*50}")
    print(f"▶  {desc}")
    print(f"{'─'*50}")
    result = subprocess.run([sys.executable] + cmd)
    if result.returncode != 0:
        print(f"\n❌ Error en: {' '.join(cmd)}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Ciclo completo TicWatch Analyzer")
    parser.add_argument("--sin-retrieve", action="store_true",
                        help="Salta la descarga, usa .tcx ya existentes")
    parser.add_argument("--dias",         type=int, default=None,
                        help="Solo últimos N días en retrieve")
    parser.add_argument("--forzar-todo",  action="store_true",
                        help="Fuerza re-descarga y re-importación de todo")
    args = parser.parse_args()

    start = datetime.now()
    print(f"\n🏃 TicWatch Analyzer — {start.strftime('%Y-%m-%d %H:%M')}")

    if not args.sin_retrieve:
        retrieve_args = ["retrieve.py"]
        if args.forzar_todo:
            retrieve_args.append("--todo")
        elif args.dias:
            retrieve_args += ["--dias", str(args.dias)]
        if not run(retrieve_args, "Descargando archivos .tcx de Mobvoi"):
            sys.exit(1)

    parse_args = ["parse.py"]
    if not run(parse_args, "Importando .tcx a la base de datos"):
        sys.exit(1)

    if not run(["stats.py"], "Generando informe HTML"):
        sys.exit(1)

    elapsed = (datetime.now() - start).total_seconds()
    print(f"\n{'═'*50}")
    print(f"✅ Completado en {elapsed:.1f}s")
    print(f"   Abre el informe: xdg-open informe.html")
    print(f"{'═'*50}\n")


if __name__ == "__main__":
    main()
