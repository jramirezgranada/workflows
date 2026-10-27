# Instalación — Automatización de Code Review y PRE RTD

Guía para dejar funcionando los 5 workflows de n8n y el worker en el contenedor.

## Archivos que necesitas

| Archivo | Para qué |
|---|---|
| Los 5 workflows (`.json`) | WF1–WF5 de n8n |
| `cr-worker.py` | Worker que corre el agente de Kiro en el contenedor |
| `.cr-worker.env` | Plantilla de configuración del worker |
| `data-tables-automatizacion.md` | Estructura de las tablas `cr_jobs` y `prertd_jobs` |
| `credenciales-n8n.md` | Cómo crear las credenciales |
| `kiro-cli-login-contenedor.md` | Cómo iniciar sesión en Kiro CLI dentro del contenedor |

## Requisitos

- Una instancia de **n8n** accesible por HTTPS desde el contenedor (probado en n8n 2.x, que tiene Data Tables).
- Acceso al **contenedor SSH** de la empresa (con VPN) y Kiro IDE.
- **Kiro CLI** instalado en Windows y con sesión iniciada.
- El agente de code review (por ejemplo `dms-reviewer`) configurado en el contenedor (`~/.kiro/agents/`).

> **Si compartes el n8n con otra persona:** usa nombres propios para las tablas (`cr_jobs_<nombre>`, `prertd_jobs_<nombre>`), los workflows y los paths de los webhooks (`cr/next-job-<nombre>`, `cr/result-<nombre>`). Si no, las colas se mezclan. Si cambias los paths, ajústalos también en `cr-worker.py` (función `call`).

---

## Paso 1 — Credenciales en n8n

Sigue **`credenciales-n8n.md`** y crea:

- `JiraCredentials` (Basic Auth) y la credencial **Jira SW Cloud API**
- `Bitbucket CR` (Basic Auth, token con scopes)
- `Telegram CR Bot` (Telegram API), y anota tu **chat_id**
- `X-CR-Token` (Header Auth), y guarda el token para el worker

## Paso 2 — Data Tables

Sigue **`data-tables-automatizacion.md`** y crea `cr_jobs` y `prertd_jobs` con todas sus columnas (tipo String).

## Paso 3 — Importar los workflows

En n8n: **Overview → Create workflow → ⋯ → Import from File**. Importa en este orden:

1. `PRE RTD - Procesar` (WF5), porque el WF4 lo llama.
2. `PRE RTD - Detectar` (WF4)
3. `CR - Resultado` (WF3)
4. `CR - API worker` (WF2)
5. `CR - Detectar tickets` (WF1)

## Paso 4 — Ajustar cada workflow

### 4.1 Credenciales (todos los workflows)
Abre cada nodo que use una credencial y **selecciona la tuya**:
- Nodos **HTTP Request** de Jira → `JiraCredentials`
- Nodos **HTTP Request** de Bitbucket → `Bitbucket CR`
- Nodos **Jira Software** → tu credencial Jira SW Cloud API
- Nodos **Telegram** → `Telegram CR Bot`
- Nodos **Webhook** (WF2 y WF3) → `X-CR-Token`

### 4.2 Valores personales

| Valor | Dónde cambiarlo |
|---|---|
| **Tu accountId de Atlassian** | Variable `yo` en `Extraer dev` (WF3) y en `Analizar ticket` (WF5) |
| **Tu chat_id de Telegram** | Campo **Chat ID** de todos los nodos de Telegram |
| **Tablas** (si usas nombres propios) | Todos los nodos **Data table** |
| **Paths de los webhooks** (si usas propios) | Nodos **Webhook** de WF2 y WF3 |

**Cómo obtener tu accountId:** en un nodo HTTP Request, haz `GET https://devactiva.atlassian.net/rest/api/3/myself` con `JiraCredentials`; el campo `accountId` es el tuyo.

### 4.3 Valores del equipo (cambian solo si cambia el proceso)

| Valor | Dónde está |
|---|---|
| Workspace de Bitbucket `fordar` | URLs de Bitbucket en WF3 |
| accountId de Ariel | `Asignar a Ariel` (WF3) y `Asignar a Ariel PRE RTD` (WF5) |
| Transición **CR Rejected** = `14` | `Jira CR REJECTED` (WF3) |
| Transición **RTD QA** = `13` | `Jira RTD QA` (WF3) |
| Transición **RTD** = `26` | `Jira RTD` (WF5) |
| JQL `status = "CODE REVIEW"` / `"PRE-RTD"` | Nodos Jira de WF1 y WF4 |

### 4.4 Zona horaria
En WF1 y WF4: **⋯ → Settings → Timezone → `America/Bogota`** (o la tuya).

### 4.5 WF4 → WF5
En WF4, nodo **`Procesar ticket`**: verifica que apunte a **tu** `PRE RTD - Procesar` y que **Wait For Sub-Workflow Completion** esté activado.

## Paso 5 — Publicar

Publica en este orden: **WF5 → WF4 → WF3 → WF2 → WF1**.

> Cada vez que cambies algo, vuelve a **publicar**. Si no, producción sigue con la versión anterior.

---

## Paso 6 — Kiro CLI en el contenedor

Sigue **`kiro-cli-login-contenedor.md`**. Al final, debe funcionar:
```bash
export PATH="$HOME/.local/bin:$PATH"
kiro-cli whoami
kiro-cli chat --no-interactive --agent dms-reviewer "Responde únicamente OK"
```

## Paso 7 — Instalar el worker

1. Copia `cr-worker.py` a `/root/cr-worker.py` y `.cr-worker.env` a `/root/.cr-worker.env`. Puedes arrastrarlos desde Kiro IDE.
2. Llena el `.env`:
   ```
   CR_TOKEN=<el mismo token de la credencial X-CR-Token>
   CR_BASE=https://<tu-n8n>
   CR_HOOK=webhook
   ```
3. Protégelo y verifica la sintaxis:
   ```bash
   chmod 600 /root/.cr-worker.env
   python3 -m py_compile /root/cr-worker.py && echo "SINTAXIS OK"
   ```
4. Revisa las constantes del inicio de `cr-worker.py`: `AGENT`, `WORKDIR` (la carpeta con el steering del agente) y `KIRO`.
5. Prueba la conexión con n8n:
   ```bash
   source /root/.cr-worker.env
   curl -s -H "X-CR-Token: $CR_TOKEN" "$CR_BASE/webhook/cr/next-job"
   ```
   Debe responder `{"job": null}`.

---

## Paso 8 — Pruebas

### Code Review
1. Ejecuta **WF1** a mano (**Execute workflow**). Los tickets en CODE REVIEW asignados a ti aparecen en `cr_jobs` como `pending`, y te llega el aviso 📥.
   - Si no tienes ninguno, agrega una fila a mano: `ticket_key`, `status = pending`, `active = yes`.
2. Corre el worker con un ticket:
   ```bash
   python3 /root/cr-worker.py --ticket DEV-XXXX
   ```
3. Unos 2 minutos después te llega a Telegram el mensaje con el botón **Decidir**.
4. Para la primera prueba, elige **Descartar**: no toca nada.

### PRE RTD
1. Ejecuta **WF4** a mano.
2. Por cada ticket en PRE-RTD te llega, de a uno:
   - ⚠️ **Sin DDP**, o 🔗 **Manual**, solo aviso; o
   - 🚀 Un mensaje con DDP, PRs y botones **Aprobar / Descartar**.

> ⚠️ **Aprobar y Rechazar son acciones reales** en Jira y Bitbucket. Úsalos solo con tickets que de verdad estén listos.

---

## Uso diario

| Cuándo | Qué pasa | Qué haces |
|---|---|---|
| Por horario (WF1 y WF4) | Se encolan los CODE REVIEW y PRE-RTD nuevos | Nada |
| En la mañana | — | `python3 /root/cr-worker.py --once` |
| Durante el día | Llegan los formularios a Telegram | Decides en cada uno |

**Comandos del worker:**
```bash
python3 /root/cr-worker.py --once              # toda la cola y termina
python3 /root/cr-worker.py --ticket DEV-XXXX   # un solo ticket
python3 /root/cr-worker.py                     # modo continuo
```

## Problemas frecuentes

| Síntoma | Causa / solución |
|---|---|
| `Authorization data is wrong` | El token del `.env` no coincide con la credencial `X-CR-Token` |
| `HTTP Error 404` en el worker | WF2 o WF3 no están publicados, o el path del webhook es distinto |
| Llega ⚠️ error y el log dice `Not logged in` | Venció la sesión de Kiro: repite `kiro-cli-login-contenedor.md` |
| Telegram: `can't parse entities` | Un texto trae `_`, `*` o `[`: escápalo con `.replace(/([_*\`\[])/g, '\\$1')` |
| `Referenced node doesn't exist` | Un nodo se renombró: ajusta el nombre en las expresiones `$('...')` |
| Los cambios no se reflejan | Falta **publicar** el workflow |
| Un ticket no se vuelve a encolar | Tiene una fila con `active = yes`: ponla en `no`, o en `pending` para repetir |
| `--ticket` responde que no está pendiente | La fila debe tener `status = pending` y `active = yes`, y la key escrita igual |

Los informes completos de cada review quedan en `/root/cr-runs/`.
