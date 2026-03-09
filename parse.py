#!/usr/bin/env python3
"""
parse.py — Parsea los archivos .tcx y los guarda en SQLite

Uso:
    python3 parse.py                    # procesa todos los .tcx de TCX_DIR
    python3 parse.py ruta/a/archivo.tcx # procesa un único fichero
"""

import os
import sys
import shutil
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv  # type: ignore

load_dotenv()

TCX_DIR       = Path(os.getenv("TCX_DIR", "tcx")).expanduser()
DB_PATH       = Path(os.getenv("DB_PATH", "ejercicios.db")).expanduser()
PROCESSED_DIR = Path(os.getenv("PROCESSED_DIR", "tcx_procesados")).expanduser()

# Namespace XML del formato TCX de Garmin (que usa Mobvoi)
NS = {
    "tcx":  "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2",
    "ax":   "http://www.garmin.com/xmlschemas/ActivityExtension/v2",
    "ns3":  "http://www.garmin.com/xmlschemas/ActivityExtension/v2",
}

# ──────────────────────────────────────────────
# Base de datos
# ──────────────────────────────────────────────
def init_db(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS actividades (
            id              TEXT PRIMARY KEY,   -- motion_id (nombre del fichero sin .tcx)
            fichero         TEXT NOT NULL,
            fecha           TEXT NOT NULL,      -- YYYY-MM-DD
            hora_inicio     TEXT,               -- HH:MM
            hora_fin        TEXT,               -- HH:MM
            tipo_actividad  TEXT,               -- Running, Cycling, etc.
            duracion_seg    INTEGER,            -- segundos totales
            distancia_m     REAL,               -- metros
            calorias        INTEGER,
            fc_media        INTEGER,            -- bpm
            fc_max          INTEGER,            -- bpm
            velocidad_media REAL,               -- m/s
            puntos_gps      INTEGER,            -- número de trackpoints con GPS
            importado_en    TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_fecha ON actividades(fecha);
        CREATE INDEX IF NOT EXISTS idx_tipo  ON actividades(tipo_actividad);
    """)
    conn.commit()


# ──────────────────────────────────────────────
# Parser TCX
# ──────────────────────────────────────────────
def parse_tcx(path: Path) -> dict | None:
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        print(f"  ✗ XML malformado en {path.name}: {e}")
        return None

    root = tree.getroot()

    # El elemento principal puede estar con o sin namespace
    def find(node, tag):
        result = node.find(f"tcx:{tag}", NS)
        if result is None:
            result = node.find(tag)
        return result

    def findall(node, tag):
        result = node.findall(f"tcx:{tag}", NS)
        if not result:
            result = node.findall(tag)
        return result

    def text(node, tag, default=None):
        el = find(node, tag)
        return el.text.strip() if el is not None and el.text else default

    # Actividad raíz
    activities = root.findall(".//tcx:Activity", NS) or root.findall(".//Activity")
    if not activities:
        return None

    act = activities[0]

    # Tipo de deporte
    sport = act.get("Sport", "Unknown")

    # Laps
    laps = findall(act, "Lap")
    if not laps:
        return None

    # Tiempo de inicio del primer lap
    start_time_str = laps[0].get("StartTime", "")
    try:
        if start_time_str.endswith("Z"):
            start_dt = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
        else:
            start_dt = datetime.fromisoformat(start_time_str)
        # Convertir a hora local (CET/CEST = UTC+1 / UTC+2)
        # Usamos offset fijo UTC+1 como aproximación (España peninsular invierno)
        from datetime import timedelta
        local_dt = start_dt.astimezone(timezone.utc).replace(tzinfo=None)
        local_dt = local_dt + timedelta(hours=1)  # UTC+1 básico
    except Exception:
        local_dt = None

    fecha      = local_dt.strftime("%Y-%m-%d") if local_dt else ""
    hora_ini   = local_dt.strftime("%H:%M")    if local_dt else ""

    # Acumular datos de todos los laps
    total_seg   = 0.0
    total_m     = 0.0
    total_cal   = 0
    fc_values   = []
    track_count = 0
    last_time   = None

    for lap in laps:
        # Duración
        tt = text(lap, "TotalTimeSeconds")
        if tt:
            try:
                total_seg += float(tt)
            except ValueError:
                pass

        # Distancia
        dist = text(lap, "DistanceMeters")
        if dist:
            try:
                total_m += float(dist)
            except ValueError:
                pass

        # Calorías
        cal = text(lap, "Calories")
        if cal:
            try:
                total_cal += int(float(cal))
            except ValueError:
                pass

        # FC media del lap
        avg_fc_el = find(lap, "AverageHeartRateBpm")
        if avg_fc_el is not None:
            v = text(avg_fc_el, "Value")
            if v:
                try:
                    fc_values.append(float(v))
                except ValueError:
                    pass

        # FC máxima del lap
        max_fc_el = find(lap, "MaximumHeartRateBpm")
        if max_fc_el is None:
            max_fc_el = lap.find("tcx:MaximumHeartRateBpm", NS)
        # (la procesamos abajo)

        # Trackpoints — para GPS y FC punto a punto
        for tp in lap.findall(".//tcx:Trackpoint", NS) or lap.findall(".//Trackpoint"):
            pos = find(tp, "Position")
            if pos is not None:
                lat = text(pos, "LatitudeDegrees")
                lon = text(pos, "LongitudeDegrees")
                if lat and lon:
                    track_count += 1

            # FC por punto (más precisa que la media del lap)
            hr_el = find(tp, "HeartRateBpm")
            if hr_el is not None:
                v = text(hr_el, "Value")
                if v:
                    try:
                        fc_values.append(float(v))
                    except ValueError:
                        pass

            # Tiempo del último punto
            t = text(tp, "Time")
            if t:
                last_time = t

    # FC media y máxima
    fc_media = round(sum(fc_values) / len(fc_values)) if fc_values else None
    fc_max   = round(max(fc_values))                  if fc_values else None

    # Hora de fin
    hora_fin = ""
    if last_time:
        try:
            if last_time.endswith("Z"):
                end_dt = datetime.fromisoformat(last_time.replace("Z", "+00:00"))
            else:
                end_dt = datetime.fromisoformat(last_time)
            from datetime import timedelta
            end_local = end_dt.astimezone(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
            hora_fin = end_local.strftime("%H:%M")
        except Exception:
            pass

    # Velocidad media (m/s)
    vel_media = (total_m / total_seg) if total_seg > 0 and total_m > 0 else None

    # Normalizar tipo de actividad
    sport_norm = normalizar_tipo(sport)

    return {
        "id":              path.stem,
        "fichero":         path.name,
        "fecha":           fecha,
        "hora_inicio":     hora_ini,
        "hora_fin":        hora_fin,
        "tipo_actividad":  sport_norm,
        "duracion_seg":    int(total_seg),
        "distancia_m":     round(total_m, 1) if total_m > 0 else None,
        "calorias":        total_cal or None,
        "fc_media":        fc_media,
        "fc_max":          fc_max,
        "velocidad_media": round(vel_media, 3) if vel_media else None,
        "puntos_gps":      track_count,
        "importado_en":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def normalizar_tipo(sport: str) -> str:
    """Convierte los tipos de Mobvoi/Garmin a nombres legibles en español."""
    mapa = {
        "Running":           "Carrera",
        "Treadmill":         "Cinta (correr)",
        "Cycling":           "Ciclismo",
        "IndoorCycling":     "Ciclismo indoor",
        "Swimming":          "Natación",
        "Walking":           "Caminar",
        "Hiking":            "Senderismo",
        "Other":             "Otro",
        "Strength":          "Musculación",
        "WeightTraining":    "Musculación",
        "Yoga":              "Yoga",
        "Pilates":           "Pilates",
        "Rowing":            "Remo",
        "Elliptical":        "Elíptica",
        "Soccer":            "Fútbol",
        "Basketball":        "Baloncesto",
        "Tennis":            "Tenis",
        "Badminton":         "Bádminton",
    }
    # Búsqueda exacta, luego parcial
    if sport in mapa:
        return mapa[sport]
    for k, v in mapa.items():
        if k.lower() in sport.lower():
            return v
    return sport  # devolver tal cual si no se reconoce


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    ficheros = []
    if len(sys.argv) > 1:
        ficheros = [Path(f) for f in sys.argv[1:]]
    else:
        if not TCX_DIR.exists():
            print(f"❌ Carpeta {TCX_DIR} no existe. Ejecuta primero: python3 retrieve.py")
            sys.exit(1)
        ficheros = sorted(TCX_DIR.glob("*.tcx"))

    if not ficheros:
        print(f"ℹ️  No hay ficheros .tcx en {TCX_DIR}")
        return

    print(f"📂 Procesando {len(ficheros)} ficheros .tcx → {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    ok = errors = skip = 0
    for path in ficheros:
        data = parse_tcx(path)
        if data is None:
            errors += 1
            continue
        try:
            conn.execute("""
                INSERT OR REPLACE INTO actividades VALUES (
                    :id, :fichero, :fecha, :hora_inicio, :hora_fin,
                    :tipo_actividad, :duracion_seg, :distancia_m, :calorias,
                    :fc_media, :fc_max, :velocidad_media, :puntos_gps, :importado_en
                )
            """, data)
            ok += 1
            dur_min = data["duracion_seg"] // 60
            print(f"  ✓ {data['fecha']}  {data['tipo_actividad']:<20} {dur_min:3d} min  {data['calorias'] or '?':>5} kcal  FC:{data['fc_media'] or '?':>4} bpm")
            # Mover a procesados solo si el fichero está en TCX_DIR (no si se pasó a mano)
            if path.parent.resolve() == TCX_DIR.resolve():
                dest = PROCESSED_DIR / path.name
                shutil.move(str(path), str(dest))
        except Exception as e:
            print(f"  ✗ {path.name}: {e}")
            errors += 1

    conn.commit()
    conn.close()

    print(f"\n✅ Importados: {ok}   Errores: {errors}")
    print(f"   Base de datos: {DB_PATH.resolve()}")
    if ok:
        print(f"   TCX procesados en: {PROCESSED_DIR.resolve()}")
    print("\nAhora ejecuta:  python3 stats.py")


if __name__ == "__main__":
    main()
