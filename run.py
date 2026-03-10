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


LOG_FILE = Path("run.log")


def log(msg: str, file=None):
    """Imprime en consola y añade al log."""
    print(msg)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


def run(cmd: list[str], desc: str) -> bool:
    sep = "─" * 50
    log(f"\n{sep}")
    log(f"▶  {desc}")
    log(f"{sep}")
    result = subprocess.run(
        [sys.executable] + cmd,
        capture_output=False,   # salida en tiempo real en consola
    )
    # Registrar solo el resultado en el log (la salida del subproceso va a consola directa)
    status = "✅ OK" if result.returncode == 0 else f"❌ Error (código {result.returncode})"
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"   → {' '.join(cmd)}: {status}\n")
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
    header = f"\n{'═'*50}\n🏃 TicWatch Analyzer — {start.strftime('%Y-%m-%d %H:%M:%S')}\n{'═'*50}"
    log(header)

    # Argumentos usados
    flags = []
    if args.sin_retrieve: flags.append("--sin-retrieve")
    if args.dias:         flags.append(f"--dias {args.dias}")
    if args.forzar_todo:  flags.append("--forzar-todo")
    if flags:
        log(f"   Opciones: {' '.join(flags)}")

    if not args.sin_retrieve:
        retrieve_args = ["retrieve.py"]
        if args.forzar_todo:
            retrieve_args.append("--todo")
        elif args.dias:
            retrieve_args += ["--dias", str(args.dias)]
        if not run(retrieve_args, "Descargando archivos .tcx de Mobvoi"):
            log(f"   ⛔ Abortado a las {datetime.now().strftime('%H:%M:%S')}")
            sys.exit(1)

    if not run(["parse.py"], "Importando .tcx a la base de datos"):
        log(f"   ⛔ Abortado a las {datetime.now().strftime('%H:%M:%S')}")
        sys.exit(1)

    if not run(["stats.py"], "Generando informe HTML"):
        log(f"   ⛔ Abortado a las {datetime.now().strftime('%H:%M:%S')}")
        sys.exit(1)

    elapsed = (datetime.now() - start).total_seconds()
    footer = (
        f"\n{'═'*50}\n"
        f"✅ Completado en {elapsed:.1f}s — {datetime.now().strftime('%H:%M:%S')}\n"
        f"   Abre el informe: xdg-open informe.html\n"
        f"{'═'*50}\n"
    )
    log(footer)


if __name__ == "__main__":
    main()
