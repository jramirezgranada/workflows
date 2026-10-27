# Credenciales para la automatización de Code Review y PRE RTD

Cada persona debe crear **sus propias credenciales**: los workflows actúan en Jira, Bitbucket y Telegram **a nombre de quien las configura**.

> ⚠️ Nunca compartas tokens por chat ni los subas a un repo. Si alguno queda expuesto, revócalo y crea uno nuevo.

Las credenciales se crean en n8n en **Credentials → Add credential**.

---

## 1. Jira (`JiraCredentials`)

Usada por los nodos HTTP de Jira (transiciones, asignaciones, comentarios, fecha de vencimiento, historial).

**Crear el token**
1. Entra a https://id.atlassian.com/manage-profile/security/api-tokens
2. Haz clic en **Create API token** (el clásico, sin scopes).
3. Nombre: `n8n-jira`.
4. Copia el token. Solo se muestra una vez.

**En n8n**
- Tipo: **Basic Auth**
- **User:** tu email de Atlassian
- **Password:** el token
- Nombre: `JiraCredentials`

**Credencial del nodo Jira Software**

Los nodos *Jira Software* (los de la consulta JQL en WF1 y WF4) usan otro tipo de credencial, con el **mismo token**:
- Tipo: **Jira SW Cloud API**
- **Email:** tu email de Atlassian
- **API Token:** el mismo token
- **Domain:** `https://devactiva.atlassian.net`

---

## 2. Bitbucket (`Bitbucket CR`)

Usada para leer, comentar, aprobar y marcar *Request changes* en los PRs.

**Crear el token**
1. Entra a https://id.atlassian.com/manage-profile/security/api-tokens
2. Haz clic en **Create API token with scopes**.
3. Nombre: `n8n-bitbucket`.
4. App: **Bitbucket**.
5. Scopes:
   - `read:repository:bitbucket`
   - `read:pullrequest:bitbucket`
   - `write:pullrequest:bitbucket`
6. Copia el token.

**En n8n**
- Tipo: **Basic Auth**
- **User:** tu email de Atlassian
- **Password:** el token de Bitbucket
- Nombre: `Bitbucket CR`

> ⚠️ No uses el token de Bitbucket en los nodos de Jira, ni al revés: cada uno solo funciona en su servicio.

**Prueba rápida:** un nodo HTTP Request con `GET https://api.bitbucket.org/2.0/repositories/fordar/<repo>/pullrequests/<id>` y esta credencial debe devolver el PR.

---

## 3. Telegram (bot propio)

Usada para recibir los avisos y los formularios de decisión.

**Crear el bot**
1. En Telegram, abre **@BotFather** y envía `/newbot`.
2. Elige un nombre (por ejemplo `CR Reviewer`) y un username que termine en `bot`.
3. BotFather te da un **token** del tipo `123456789:AAH...`. Guárdalo.
4. Abre tu bot y envíale cualquier mensaje (por ejemplo `hola`).

**Obtener tu chat_id**
1. Abre en el navegador: `https://api.telegram.org/bot<TOKEN>/getUpdates`
2. Busca `"chat":{"id":123456789,...}`. Ese número es tu **chat_id**.
3. Si sale `"result":[]`, envíale otro mensaje al bot y recarga.

**En n8n**
- Tipo: **Telegram API**
- **Access Token:** el token del bot
- Nombre: `Telegram CR Bot`

Después, pon tu **chat_id** en el campo **Chat ID** de todos los nodos de Telegram.

---

## 4. Token del webhook del worker (`X-CR-Token`)

Protege los webhooks `cr/next-job` y `cr/result`, para que solo tu worker pueda usarlos.

**Generar el token** (en el contenedor):
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**En n8n**
- Tipo: **Header Auth**
- **Name:** `X-CR-Token`
- **Value:** el token generado
- Úsala en los nodos **Webhook** de **WF2** y **WF3**.

**En el contenedor**, pon el mismo valor en `/root/.cr-worker.env`:
```
CR_TOKEN=<el mismo token>
CR_BASE=https://<tu-n8n>
CR_HOOK=webhook
```
```bash
chmod 600 /root/.cr-worker.env
```

**Prueba:**
```bash
source /root/.cr-worker.env
curl -s -H "X-CR-Token: $CR_TOKEN" "$CR_BASE/webhook/cr/next-job"
```
Debe responder `{"job": null}` o un trabajo. Si dice *Authorization data is wrong*, los valores no coinciden.

---

## Resumen

| Credencial | Tipo en n8n | Dónde se usa |
|---|---|---|
| `JiraCredentials` | Basic Auth (email + token Jira) | Nodos HTTP de Jira (WF3, WF5) |
| Jira SW Cloud API | Jira SW Cloud API (mismo token) | Nodos Jira Software (WF1, WF4) |
| `Bitbucket CR` | Basic Auth (email + token Bitbucket) | Nodos HTTP de Bitbucket (WF3, WF5) |
| `Telegram CR Bot` | Telegram API | Todos los nodos de Telegram |
| `X-CR-Token` | Header Auth | Webhooks de WF2 y WF3 |

Después de importar los workflows, abre cada nodo que use credenciales y **selecciona las tuyas**.
