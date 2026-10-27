# Data Tables — Automatización Code Review y PRE RTD

Todas las columnas son de tipo **String**. Los campos `id`, `createdAt` y `updatedAt` los crea n8n automáticamente.

> ⚠️ Los nombres de las tablas y columnas deben coincidir **exactamente** (minúsculas, guion bajo), porque los nodos los referencian por nombre.

---

## 1. `cr_jobs` — Cola de Code Review

Usada por: **WF1** (Detectar), **WF2** (API worker) y **WF3** (Resultado).

| Columna | Descripción | Valores / ejemplo |
|---|---|---|
| `ticket_key` | Key del ticket de Jira | `DEV-4851` |
| `summary` | Título del ticket | `Ajuste de reporte de unidades` |
| `status` | Estado del trabajo | ver tabla de estados |
| `active` | Si el ticket está activo en la cola | `yes` / `no` |
| `developer_account_id` | accountId de Atlassian del dev (se llena al rechazar) | `712020:...` |
| `developer_name` | Nombre del dev | `Facundo Gil` |
| `pr_url` | URL del PR revisado | `https://bitbucket.org/fordar/repo/pull-requests/67` |
| `report_md` | Informe completo del agente | texto markdown |
| `blockers_json` | Bloqueantes del agente en JSON | `[{"archivo":"...","linea":10,...}]` |

### Estados (`status`) de `cr_jobs`

| Valor | Significado | `active` |
|---|---|---|
| `pending` | En cola, esperando al worker | `yes` |
| `running` | El worker lo está revisando | `yes` |
| `done` | Revisado; esperando la decisión en Telegram | `yes` |
| `error` | El agente falló o no devolvió JSON válido | `yes` |
| `manual` | Tiene vínculos *implements* / *is implemented by*; se revisa a mano | `yes` |
| `approved` | Aprobado: PR aprobado, ticket en RTD QA y asignado a Ariel | `no` |
| `rejected` | Rechazado: bloqueantes comentados, CR REJECTED y asignado al dev | `no` |
| `discarded` | Descartado por el TL; no se tocó nada | `yes` |

---

## 2. `prertd_jobs` — Cola de PRE RTD

Usada por: **WF4** (Detectar) y **WF5** (Procesar).

| Columna | Descripción | Valores / ejemplo |
|---|---|---|
| `ticket_key` | Key del ticket de Jira | `DEV-4756` |
| `summary` | Título del ticket | `L4 - Como desarrollador FE...` |
| `status` | Estado del trabajo | ver tabla de estados |
| `active` | Si el ticket está activo en la cola | `yes` / `no` |
| `ddp_file` | Nombre del DDP a master encontrado | `DDP_MASTER_4756.docx` |
| `prs_json` | Lista de PRs stage → master en JSON | `[{"repo":"fordar/mfe-stock-units",...}]` |
| `dev_name` | Nombre del dev (para el aviso de sin DDP) | `Facundo Gil` |

### Estados (`status`) de `prertd_jobs`

| Valor | Significado | `active` |
|---|---|---|
| `waiting` | Encolado; esperando la decisión en Telegram | `yes` |
| `sin_ddp` | No tiene DDP a master (PRD / PROD / MASTER); se avisó con el nombre del dev | `yes` |
| `manual` | Tiene vínculos *implements* / *is implemented by*; se revisa a mano | `yes` |
| `approved` | Aprobado: PRs aprobados, ticket en RTD, asignado a Ariel y con vencimiento | `no` |
| `discarded` | Descartado por el TL; no se tocó nada | `yes` |

---

## Cómo funciona la columna `active`

- **`yes`:** el ticket ya está en la cola. Los workflows de detección **no lo vuelven a encolar** ni notificar en cada lectura.
- **`no`:** el ticket ya se cerró (aprobado o rechazado), o ya no está en el estado de Jira correspondiente.
- **Limpieza automática:** en cada lectura, WF1 y WF4 pasan a `active = no` las filas cuyos tickets ya **salieron** de CODE REVIEW o PRE-RTD. Así, si un ticket **vuelve** a ese estado (por ejemplo, después de un CR REJECTED), se encola como nuevo y se revisa otra vez.

## Tips

- Para **repetir** la revisión de un ticket de Code Review, pon su fila en `status = pending` y `active = yes`, y corre `python3 /root/cr-worker.py --ticket DEV-XXXX`.
- Si comparten el mismo n8n con otra persona, cada uno debe tener **sus propias tablas** (por ejemplo `cr_jobs_nombre`, `prertd_jobs_nombre`) y actualizar los nodos Data table de sus workflows para que apunten a ellas.
