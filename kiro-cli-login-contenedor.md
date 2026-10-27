# Login de Kiro CLI en el contenedor SSH (copiando la sesión desde Windows)

Guía para cuando `kiro-cli` dice **Not logged in** dentro del contenedor y el login normal no funciona, porque la empresa usa **Microsoft (IdP externo)** y el contenedor no tiene navegador.

La solución es copiar la sesión que ya tienes en tu PC con Windows hacia el contenedor.

---

## Requisitos

- Kiro IDE conectado por SSH al contenedor (con la VPN activa).
- `kiro-cli` instalado en Windows **y con sesión iniciada**. En PowerShell:

  ```powershell
  kiro-cli whoami
  ```

  Debe decir `Logged in with External IdP`. Si no, corre `kiro-cli login` en Windows y completa el login en el navegador.

---

## 1. Contenedor: actualizar el CLI y confirmar el estado

```bash
export PATH="$HOME/.local/bin:$PATH"
kiro-cli update
kiro-cli whoami
```

Debe mostrar `Not logged in`.

## 2. Windows (PowerShell): copiar la base de sesión al escritorio

```powershell
Copy-Item "$env:LOCALAPPDATA\Kiro-Cli\data.sqlite3" "$env:USERPROFILE\Desktop\kiro-windows.sqlite3"
```

## 3. Subir el archivo al contenedor

En Kiro IDE (conectado al contenedor), abre la carpeta `/root` y **arrastra** `kiro-windows.sqlite3` desde el escritorio al explorador del IDE.

> ⚠️ No lo sueltes dentro de un repo: el archivo contiene tu sesión.

## 4. Contenedor: importar la sesión

```bash
F=$(find / -name "kiro-windows.sqlite3" -not -path "/proc/*" 2>/dev/null | head -1)
echo "Archivo: $F"
DB=$HOME/.local/share/kiro-cli/data.sqlite3
cp $DB $HOME/data.sqlite3.backup
python3 - "$F" "$DB" <<'EOF'
import sqlite3, sys
src = sqlite3.connect(sys.argv[1]); dst = sqlite3.connect(sys.argv[2])
tok = src.execute("select value from auth_kv where key='kirocli:external-idp:token'").fetchone()
prof = src.execute("select value from state where key='api.codewhisperer.profile'").fetchone()
if not tok: sys.exit("No hay sesión External IdP en el archivo de Windows")
dst.execute("insert or replace into auth_kv(key,value) values(?,?)", ("kirocli:external-idp:token", tok[0]))
if prof: dst.execute("insert or replace into state(key,value) values(?,?)", ("api.codewhisperer.profile", prof[0]))
dst.execute("delete from state where key in ('auth.idc.region','auth.idc.start-url')")
dst.commit(); print("Sesión importada")
EOF
kiro-cli whoami
```

Debe mostrar `Logged in with External IdP`.

## 5. Borrar las copias

En el contenedor:

```bash
rm -f "$F"
```

En Windows:

```powershell
Remove-Item "$env:USERPROFILE\Desktop\kiro-windows.sqlite3"
```

## 6. Probar un agente

```bash
kiro-cli chat --no-interactive --agent NOMBRE_DEL_AGENTE "Responde únicamente OK"
```

Debe responder `OK`.

---

## Notas

- **Restaurar si algo sale mal:**

  ```bash
  cp $HOME/data.sqlite3.backup $HOME/.local/share/kiro-cli/data.sqlite3
  ```

- El PC y el contenedor quedan **compartiendo la misma sesión**. Si el contenedor vuelve a decir `Not logged in`, repite los pasos 2 a 5.
- Hazlo solo con **tu propia cuenta** y en el contenedor de **tu propio trabajo**.
- ¿Por qué no funciona `kiro-cli login --use-device-flow`? La opción "Your Organization" del CLI es para IAM Identity Center (pide una Start URL tipo `awsapps.com`). El login con Microsoft solo funciona con navegador, que el contenedor no tiene.
