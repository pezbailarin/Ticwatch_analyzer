#!/usr/bin/env python3
"""
retrieve.py — Descarga todos los archivos .tcx de h.mobvoi.com

Uso:
    python3 retrieve.py              # descarga actividades nuevas (no descargadas antes)
    python3 retrieve.py --todo       # fuerza la re-descarga de todo
    python3 retrieve.py --dias 30    # solo actividades de los últimos N días

Requiere: WW_TOKEN y ACCOUNT_ID en el fichero .env
"""

import os
import sys
import time
import json
import argparse
import requests
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv  # type: ignore

load_dotenv()

WW_TOKEN   = os.getenv("WW_TOKEN", "")
ACCOUNT_ID = os.getenv("ACCOUNT_ID", "")
TCX_DIR    = Path(os.getenv("TCX_DIR", "tcx")).expanduser()
PAGE_SIZE  = int(os.getenv("PAGE_SIZE", "50"))

BASE_URL = "https://h.mobvoi.com"

# ──────────────────────────────────────────────
# Cabeceras comunes que imitan al navegador
# ──────────────────────────────────────────────
def _headers(session_id: str | None = None) -> dict:
    h = {
        "accept":           "application/json, text/plain, */*",
        "accept-language":  "es,es-ES;q=0.9,en;q=0.8",
        "referer":          "https://h.mobvoi.com/pages/sports",
        "cookie":           f"ww_token={WW_TOKEN}",
    }
    if session_id:
        h["cookie"] += f"; sessionId={session_id}"
    return h


# ──────────────────────────────────────────────
# Paso 1: intercambiar ww_token → session_id
# ──────────────────────────────────────────────
def get_session_id() -> str:
    """Obtiene un sessionId válido a partir del ww_token."""
    url = f"{BASE_URL}/api/mobvoiAccount/account/info/token?token={WW_TOKEN}&origin=health"
    r = requests.get(url, headers=_headers(), timeout=15)
    r.raise_for_status()
    data = r.json()
    # La respuesta devuelve el token en distintos campos según versión de la API
    session_id = (
        data.get("data", {}).get("sessionId")
        or data.get("data", {}).get("session_id")
        or data.get("sessionId")
        or data.get("data", {}).get("ww_token")
        or WW_TOKEN   # fallback: el propio ww_token actúa de sessionId
    )
    if not session_id:
        raise ValueError(f"No se pudo obtener sessionId. Respuesta: {data}")
    return session_id


# ──────────────────────────────────────────────
# Paso 2: obtener la lista paginada de actividades
# ──────────────────────────────────────────────
def get_activity_list(session_id: str, since: datetime | None = None) -> list[dict]:
    """
    Devuelve la lista completa de actividades (todos los motionId).
    Endpoint confirmado: /api/sportWear3/data/accounts/{id}/records/page/motion
    Parámetros: pageNo (base 1), pageSize, sessionId, motionType (opcional)
    """
    LIST_ENDPOINT = (
        f"{BASE_URL}/api/sportWear3/data/accounts/{ACCOUNT_ID}"
        f"/records/page/motion"
    )

    all_activities = []
    page_no = 1

    while True:
        params = {
            "pageNo":    page_no,
            "pageSize":  PAGE_SIZE,
            "sessionId": session_id,
            "motionType": "",   # vacío = todos los tipos
        }

        r = requests.get(LIST_ENDPOINT, params=params, headers=_headers(session_id), timeout=15)
        r.raise_for_status()
        data = r.json()

        # La respuesta tiene: data.list (actividades) y data.total (total de registros)
        inner = data.get("data") or data
        records = (
            inner.get("list")
            or inner.get("records")
            or inner.get("motions")
            or []
        )

        if not records:
            break

        # Filtro por fecha si se pidió --dias
        if since:
            since_ts = since.timestamp() * 1000  # ms epoch
            records_filtrados = []
            for rec in records:
                # startTime puede ser ms epoch o string ISO
                st = rec.get("startTime") or rec.get("start_time") or 0
                if isinstance(st, (int, float)) and st >= since_ts:
                    records_filtrados.append(rec)
                elif isinstance(st, str) and st[:10] >= since.strftime("%Y-%m-%d"):
                    records_filtrados.append(rec)
            if not records_filtrados:
                break   # ya llegamos a fechas anteriores al límite
            records = records_filtrados

        all_activities.extend(records)
        print(f"  Página {page_no}: {len(records)} actividades ({len(all_activities)} total)")

        total = inner.get("total") or inner.get("totalCount") or 0
        if len(all_activities) >= total or len(records) < PAGE_SIZE:
            break

        page_no += 1
        time.sleep(0.3)   # cortesía: no saturar el servidor

    return all_activities


# ──────────────────────────────────────────────
# Paso 3: descargar un .tcx individual
# ──────────────────────────────────────────────
def download_tcx(motion_id: str, session_id: str) -> bytes:
    url = (
        f"{BASE_URL}/api/sportWear3/data/accounts/{ACCOUNT_ID}"
        f"/records/motion/tcx/download"
    )
    params = {"motionId": motion_id, "sessionId": session_id}
    r = requests.get(url, params=params, headers=_headers(session_id), timeout=30)
    r.raise_for_status()
    return r.content


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Descarga .tcx de Mobvoi TicWatch")
    parser.add_argument("--todo",  action="store_true", help="Re-descarga todo aunque ya exista")
    parser.add_argument("--dias",  type=int, default=None, help="Solo últimos N días")
    args = parser.parse_args()

    # Validaciones básicas
    if not WW_TOKEN:
        print("❌ Falta WW_TOKEN en .env")
        print("   Instrucciones en el README para obtenerlo.")
        sys.exit(1)
    if not ACCOUNT_ID:
        print("❌ Falta ACCOUNT_ID en .env")
        sys.exit(1)

    TCX_DIR.mkdir(parents=True, exist_ok=True)

    since = None
    if args.dias:
        since = datetime.now() - timedelta(days=args.dias)
        print(f"🔍 Buscando actividades desde {since.strftime('%Y-%m-%d')}")

    print("🔑 Obteniendo sesión...")
    session_id = get_session_id()
    print(f"   sessionId: {session_id[:8]}...")

    print("\n📋 Obteniendo lista de actividades...")
    activities = get_activity_list(session_id, since=since)
    print(f"\n   Total encontradas: {len(activities)}")

    if not activities:
        print("ℹ️  No hay actividades que descargar.")
        return

    # Filtrar las que ya existen (salvo --todo)
    to_download = []
    for act in activities:
        motion_id = (
            act.get("motionId")
            or act.get("motion_id")
            or act.get("id")
            or act.get("recordId")
            or ""
        )
        if not motion_id:
            continue
        dest = TCX_DIR / f"{motion_id}.tcx"
        if not args.todo and dest.exists():
            continue
        to_download.append((motion_id, act))

    print(f"   Por descargar: {len(to_download)} (ya descargadas: {len(activities)-len(to_download)})")

    if not to_download:
        print("✅ Todo actualizado, nada que descargar.")
        return

    # Descargar
    ok = 0
    errors = 0
    for i, (motion_id, act) in enumerate(to_download, 1):
        dest = TCX_DIR / f"{motion_id}.tcx"
        sport = (
            act.get("motionTypeName")
            or act.get("sportName")
            or act.get("sport_name")
            or act.get("exerciseName")
            or act.get("motionType")
            or "?"
        )
        # startTime puede ser ms epoch → convertir a fecha legible
        st = act.get("startTime") or act.get("start_time") or act.get("date") or ""
        if isinstance(st, (int, float)) and st > 1e10:
            from datetime import timezone
            date_str = datetime.fromtimestamp(st / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        else:
            date_str = str(st)[:10]
        print(f"  [{i:3d}/{len(to_download)}] {date_str}  {sport:<25} → {dest.name}", end=" ")
        try:
            content = download_tcx(motion_id, session_id)
            dest.write_bytes(content)
            print(f"✓ ({len(content)//1024} KB)")
            ok += 1
        except Exception as e:
            print(f"✗ ERROR: {e}")
            errors += 1
        time.sleep(0.2)

    print(f"\n✅ Descargados: {ok}   Errores: {errors}")
    print(f"   Archivos en: {TCX_DIR.resolve()}")
    print("\nAhora ejecuta:  python3 parse.py")


if __name__ == "__main__":
    main()
