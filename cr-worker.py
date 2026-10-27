#!/usr/bin/env python3
"""
Worker de Code Review automatizado (n8n + Kiro CLI).

Pide trabajo a n8n, ejecuta el agente de Kiro sobre el ticket y devuelve el resultado.

Uso:
  python3 cr-worker.py                    # modo continuo (consulta cada 60 s)
  python3 cr-worker.py --once             # procesa toda la cola y termina
  python3 cr-worker.py --ticket DEV-XXXX  # procesa solo ese ticket y termina

Configuración: /root/.cr-worker.env (permisos 600)
  CR_TOKEN=<token del Header Auth de n8n>
  CR_BASE=https://<tu-n8n>
  CR_HOOK=webhook            # opcional (por defecto: webhook)
"""
import json, os, re, subprocess, time, urllib.request, datetime, fcntl, sys

# --- Configuración -----------------------------------------------------------
cfg = dict(l.strip().split("=", 1) for l in open("/root/.cr-worker.env") if "=" in l)
TOKEN, BASE = cfg["CR_TOKEN"].strip(), cfg["CR_BASE"].strip().rstrip("/")
HOOK = cfg.get("CR_HOOK", "webhook").strip()

KIRO = "/root/.local/bin/kiro-cli"          # ruta de Kiro CLI
AGENT = "dms-reviewer"                      # agente de Kiro que hace el code review
WORKDIR = "/srv/www/ai-kiro-cli-toolkit"    # carpeta con el steering/skills del agente
RUNS = "/root/cr-runs"; os.makedirs(RUNS, exist_ok=True)  # informes completos de cada corrida
POLL, TIMEOUT = 60, 1200                    # segundos entre consultas / timeout del agente
TICKET = sys.argv[sys.argv.index('--ticket') + 1].upper() if '--ticket' in sys.argv else None
ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")

PROMPT = """review-pr {t}.
Reglas para esta ejecución automática:
- NO escribas nada en Bitbucket ni en Jira.
- Entrega primero el informe completo en markdown.
- Al final, imprime EXACTAMENTE un bloque así, con JSON válido:
<<<CR_JSON
{{"ticket":"{t}","repo":"","pr_id":0,"pr_url":"","veredicto":"APROBADO|CAMBIOS_REQUERIDOS","bloqueantes":[{{"archivo":"","linea":0,"regla":"","problema":"","solucion":""}}],"sugerencias":[{{"archivo":"","linea":0,"detalle":""}}],"nits":0}}
CR_JSON>>>"""


def log(m):
    print(f"{datetime.datetime.now():%F %T} {m}", flush=True)


def call(method, path, body=None):
    """Llama a un webhook de n8n con el token en el header."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{BASE}/{HOOK}/{path}", data=data, method=method,
          headers={"X-CR-Token": TOKEN, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"{}")


def review(ticket):
    """Ejecuta el agente de Kiro y extrae el JSON del final del informe."""
    out = f"{RUNS}/{ticket}-{datetime.datetime.now():%Y%m%d-%H%M%S}.md"
    try:
        p = subprocess.run([KIRO, "chat", "--no-interactive", "--agent", AGENT,
                            PROMPT.format(t=ticket)], cwd=WORKDIR, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=TIMEOUT)
        text = ANSI.sub("", p.stdout + p.stderr)
    except subprocess.TimeoutExpired:
        text = f"TIMEOUT: el agente no terminó en {TIMEOUT}s"
    open(out, "w").write(text)
    m = re.search(r"<<<CR_JSON\s*(\{.*?\})\s*CR_JSON>>>", text, re.S)
    if m:
        try:
            return "done", text[:m.start()].strip(), json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    return "error", text[-3500:], {}


# --- Un solo worker a la vez --------------------------------------------------
lock = open("/root/cr-worker.lock", "w")
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except OSError:
    sys.exit("Ya hay un worker corriendo")

# --- Bucle principal ----------------------------------------------------------
log(f"worker iniciado → {BASE}/{HOOK}")
while True:
    try:
        job = call("GET", "cr/next-job" + (f"?ticket={TICKET}" if TICKET else "")).get("job")
    except Exception as e:
        log(f"error pidiendo trabajo: {e}"); time.sleep(POLL); continue
    if not job:
        if TICKET:
            log(f'{TICKET} no está pendiente en la cola'); break
        if '--once' in sys.argv:
            log('cola vacía, termino'); break
        time.sleep(POLL); continue
    t = job["ticket_key"]; log(f"revisando {t}")
    status, report, result = review(t)
    for _ in range(3):
        try:
            call("POST", "cr/result", {"id": job["id"], "ticket_key": t, "status": status,
                                       "report_md": report, "result": result}); break
        except Exception as e:
            log(f"error enviando {t}: {e}"); time.sleep(10)
    log(f"{t} → {status} ({len(result.get('bloqueantes', []))} bloqueantes)")
    if TICKET: break
