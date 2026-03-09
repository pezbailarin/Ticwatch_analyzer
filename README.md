# ⌚ TicWatch Analyzer

Herramienta para descargar, analizar y visualizar tus registros de ejercicio del **TicWatch Pro** almacenados en [h.mobvoi.com](https://h.mobvoi.com/pages/sports).

Genera un **informe HTML interactivo** con:
- 📅 Calendario con intensidad diaria (estilo GitHub contributions)
- ⏱️ Minutos por día / mes / año / período personalizado
- 🔥 Calorías quemadas
- ❤️ Frecuencia cardíaca media
- 📋 Listado detallado de actividades con ordenación y filtros
- 📊 Gráfico de barras mensual

---

## Requisitos

- Python 3.10+
- Fedora / Linux (funciona en cualquier distro)

```bash
git clone <este-repo>
cd ticwatch-analyzer
python3 -m venv venv
*  source venv/bin/activate        # bash / zsh                              
*  venv\Scripts\Activate.ps1       # PowerShell                              
*  source venv/bin/activate.csh    # csh / tcsh                              
*  source venv/bin/activate.fish   # fish 

pip install -r requirements.txt
```

---

## Configuración — obtener el token

El script se autentica con tu `ww_token` de Mobvoi (una cadena de 32 caracteres). Para obtenerlo:

1. Abre **Edge** o **Firefox** y ve a [h.mobvoi.com/pages/sports](https://h.mobvoi.com/pages/sports)
2. Inicia sesión con tu cuenta Mobvoi
3. Pulsa **F12** → pestaña **Network** → filtra por **Fetch/XHR**
4. Recarga la página (F5)
5. Haz clic en cualquier petición que aparezca → pestaña **Headers**
6. En **Request Headers**, busca la cabecera **Cookie**
7. Copia el valor de `ww_token=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`

Luego:

```bash
cp .env.example .env
# Edita .env y pon tu ww_token y account_id
```

El `account_id` lo ves en las URLs de descarga:  
`/api/sportWear3/data/accounts/**50017569**/records/...`

---

## Uso

### Ciclo completo (recomendado)

```bash
python3 run.py
```

### Por pasos

```bash
# 1. Descargar los .tcx de Mobvoi
python3 retrieve.py              # solo novedades
python3 retrieve.py --dias 30    # últimos 30 días
python3 retrieve.py --todo       # re-descarga todo

# 2. Importar a la base de datos
python3 parse.py                 # procesa la carpeta tcx/
python3 parse.py tcx/archivo.tcx # un solo fichero

# 3. Generar el informe
python3 stats.py                 # genera informe.html
python3 stats.py --output mi_informe.html

# 4. Abrir
xdg-open informe.html
```

### Si ya tienes los .tcx descargados manualmente

```bash
# Ponlos todos en la carpeta tcx/
mkdir tcx
mv ~/Descargas/*.tcx tcx/

# Importar y generar informe
python3 parse.py
python3 stats.py
xdg-open informe.html
```

---

## Automatización con cron

```bash
# Ejecutar cada noche a las 23:00
0 23 * * * cd /ruta/al/proyecto && venv/bin/python3 run.py
```

---

## Estructura del proyecto

| Fichero | Descripción |
|---------|-------------|
| `retrieve.py` | Descarga .tcx de Mobvoi vía API |
| `parse.py` | Parsea los XML .tcx → SQLite |
| `stats.py` | Genera el informe HTML interactivo |
| `run.py` | Orquestador: retrieve → parse → stats |
| `ejercicios.db` | Base de datos SQLite (se crea automáticamente) |
| `tcx/` | Archivos .tcx descargados |
| `informe.html` | Informe generado (ábrelo en el navegador) |

---

## Token caducado

El `ww_token` puede caducar. Si el script da error de autenticación (401/403):
1. Vuelve a h.mobvoi.com → DevTools → Cookie → copia el nuevo `ww_token`
2. Actualiza `.env`

---

## Privacidad

Tus datos nunca salen de tu máquina. El script solo contacta con `h.mobvoi.com` (el servidor donde están alojados los datos que recuperas). La base de datos y el HTML se generan localmente.
