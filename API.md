# Especificación de la API – Facebook (login, sesión, páginas, publicar)

Documento para que otra IA o cliente sepa qué esperar en cada petición y en todos los casos de respuesta.  
Base: FastAPI. Ejecución: Docker. Arranque: `docker build -t api-facebook . && docker run -p 8000:8000 api-facebook`. La API queda en `http://localhost:8000`.

---

## Modelos de datos comunes

- **Cookie (para request):** `{ "name": string, "value": string }`
- **Cookie (formato respuesta login):** `{ "domain", "expirationDate"?, "hostOnly", "httpOnly", "name", "path", "sameSite", "secure", "session", "storeId", "value" }` — formato compatible con extensiones de navegador. `expirationDate` solo si no es cookie de sesión.

---

## 1. POST `/login/`

**Descripción:** Login a Facebook con email y contraseña cifrada. Si hay 2FA (aprobar en otro dispositivo), la API espera hasta que se apruebe o se agote el tiempo.

**Request body (JSON):**
```json
{
  "email": "string (obligatorio)",
  "password": "string (obligatorio; parte variable; la API construye encpass = '#PWD_BROWSER:0:1628896342:' + password)",
  "wait_2fa_seconds": 60
}
```
- `password`: solo la parte variable. La API concatena internamente `"#PWD_BROWSER:0:1628896342:" + password`.
- `wait_2fa_seconds`: opcional; segundos máximos esperando aprobación 2FA (mínimo efectivo 60).

**Respuestas:**

| Código | Cuándo | Body |
|--------|--------|------|
| **200** | Login correcto (sesión iniciada, cookie `c_user` presente). | `{ "status": "ok", "cookies": [ {...}, ... ], "session": { "name": "Nombre del usuario", "c_user": "100027565757737" } }` — `cookies` en formato navegador; `session` con el nombre de la sesión y el id (`c_user`). |
| **401** | Credenciales incorrectas: la URL tras el POST no es two_step_verification/checkpoint. | `{ "detail": "Email o contraseña incorrectos." }` |
| **408** | Tiempo agotado esperando aprobación 2FA. | `{ "detail": "Tiempo agotado esperando 2FA." }` |
| **422** | Validación fallida (falta `email`, `encpass` o tipos incorrectos). | `{ "detail": [ { "loc": ["body", "campo"], "msg": "...", "type": "..." } ] }` |
| **500** | Error de servidor (red, error interno, etc.). | `{ "detail": "mensaje de error" }` |

---

## 2. POST `/get_session/`

**Descripción:** Comprueba si las cookies de sesión son válidas y devuelve `c_user` y nombre de usuario.

**Request body (JSON):**
```json
{
  "cookies": [ { "name": "string", "value": "string" }, ... ]
}
```

**Respuestas:**

| Código | Cuándo | Body |
|--------|--------|------|
| **200** | Sesión válida. | `{ "status_code": 200, "mensaje": "Sesión activa", "c_user": "string (actorId)", "name": "string (nombre usuario)" }` |
| **200** | Sesión no válida o caducada. | `{ "status_code": 400, "mensaje": "No se encontró actorId o name en el HTML", "resultado": "Sesión caducada o no valida", "c_user": null, ... }` |

El cliente debe inspeccionar `body.status_code`: 200 = sesión activa, 400 = sesión inválida/caducada.

---

## 3. POST `/get_pages/`

**Descripción:** Obtiene las páginas de Facebook asociadas al usuario con las cookies dadas. Depende de sesión válida.

**Request body (JSON):**
```json
{
  "cookies": [ { "name": "string", "value": "string" }, ... ]
}
```

**Respuestas:**

| Código | Cuándo | Body |
|--------|--------|------|
| **200** | Siempre que la petición sea válida. | `{ "status": "ok", "resultado": ... }` — Si la sesión falla, `resultado` puede ser un objeto con `status_code` distinto de 200 y `mensaje` (ej. sesión caducada). Si todo va bien, `resultado` contiene los datos de páginas. |
| **422** | Validación fallida (p. ej. `cookies` ausente o mal formado). | `{ "detail": [ ... ] }` |

El cliente debe comprobar si `resultado` es un objeto de error (`resultado.status_code !== 200`) o la lista/datos de páginas.

---

## 4. POST `/publish/`

**Descripción:** Publica en Facebook (post con opcional título, comentario e imagen en base64). Usa las cookies y el `id` (c_user) del usuario.

**Request body (JSON):**
```json
{
  "id": "string (c_user / actorId, obligatorio)",
  "cookies": [ { "name": "string", "value": "string" }, ... ],
  "title": "string | null",
  "comment": "string | null",
  "image_base64": "string | null"
}
```

**Respuestas:**

| Código | Cuándo | Body |
|--------|--------|------|
| **200** | Publicación correcta. | `{ "status": "ok", "resultado": { "status_code": 200, "mensaje": "...", "data": { "feedback_id": "..." } } }` u otro objeto de éxito según el flujo. |
| **400** | Error de negocio (ej. error al publicar el post). | `{ "detail": "mensaje" }` — p. ej. "Error al publicar el post". |
| **422** | Validación fallida (falta `id`, `cookies`, etc.). | `{ "detail": [ ... ] }` |
| **500** | Error interno (excepción no controlada). | `{ "detail": "mensaje de error" }` |

---

## Resumen para integración

- **Login:** Solo devuelve cookies en **200**; en **401** = email/contraseña incorrectos; en **408** = 2FA no aprobada a tiempo.
- **Get session:** Código HTTP **200** siempre; mirar `body.status_code`: 200 = sesión activa, 400 = sesión caducada/inválida.
- **Get pages:** Código HTTP **200**; revisar si `resultado` tiene `status_code` de error o datos de páginas.
- **Publish:** **200** = éxito; **4xx/5xx** = error con `detail` en el body.
- Todas las respuestas de error de FastAPI (422, etc.) siguen el formato estándar con `detail` (string o lista de errores de validación).
