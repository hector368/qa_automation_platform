# KT — QA Automation Platform
### Guía para quien va a mantener el código

> **Para qué sirve este documento:** que alguien que nunca vio el repo pueda,
> al terminar la sesión, abrir un bug, encontrar el archivo correcto y
> modificarlo sin romper las otras tres aplicaciones.

---

## 1. La idea en una frase

La QA Automation Platform es **un proyecto Django que hospeda cuatro
automatizaciones de QA**, todas construidas sobre el mismo esqueleto.

No son cuatro aplicaciones distintas: es **un patrón repetido cuatro veces**.
Si quien recibe el KT entiende el patrón, entiende las cuatro. Si no lo
entiende, va a tener que aprender cuatro veces lo mismo.

Esa es la frase con la que hay que abrir la sesión.

---

## 2. El patrón (la parte que no se puede saltar)

Toda app de la plataforma tiene la misma forma:

```
apps/<nombre>/
├── views.py                 ← recibe el HTTP, no piensa
├── urls.py                  ← rutas de la app
├── exceptions.py            ← errores propios, con código y mensaje público
├── services/
│   ├── orchestrator.py      ← el guion: ordena los pasos, no hace el trabajo
│   └── *.py                 ← cada archivo hace UNA cosa
├── schemas/                 ← modelos Pydantic: el contrato entre pasos
├── prompts/*.txt            ← instrucciones para Claude, fuera del código
├── templates/<nombre>/
└── static/<nombre>/{css,js}
```

Y el flujo siempre es el mismo:

```
navegador → views.py → orchestrator.py → services/* → schemas/ (valida)
                            ↓
                      respuesta NDJSON en streaming → navegador
```

### Las cuatro reglas que explican todo el diseño

**1. `views.py` no tiene lógica.**
Recibe el request, llama al orchestrator, traduce excepciones a JSON. Si
alguien encuentra lógica de negocio en una vista, es un bug de estilo.

**2. `orchestrator.py` es el guion, no el actor.**
Dice *qué pasa y en qué orden*. Cada paso real vive en su propio módulo de
`services/`. Cuando falla algo, el orchestrator te dice **en qué paso**; el
service te dice **por qué**.

**3. Pydantic es el contrato entre pasos.**
Entre etapa y etapa los datos se validan contra un schema. Si el paso 3 recibe
basura del paso 2, revienta ahí mismo con un mensaje claro, no tres pasos
después con un `KeyError` incomprensible. Esto es lo que hace el sistema
depurable.

**4. Los prompts son archivos de texto, no strings en el código.**
`prompts/*.txt`. Se pueden ajustar sin tocar Python, sin redeploy mental, y
el diff de un cambio de prompt se lee como lo que es.

### Dos decisiones de arquitectura que van a preguntar

**No hay base de datos.** Cero modelos. Todo el estado vive en el cache de
Django con TTL. Razón: la plataforma no *guarda* información, la *transforma*
— entra un documento, sale otro. Si guardáramos, tendríamos que decidir quién
es dueño del dato, cuánto vive y quién lo borra. No guardando, no existe el
problema. El costo es que si se reinicia el servidor durante una corrida, la
corrida se pierde. Lo aceptamos.

**El streaming es NDJSON, no WebSocket.** `StreamingHttpResponse` que emite
una línea JSON por evento. Es más simple, no necesita infraestructura extra y
para "mostrar progreso de una tarea larga" alcanza de sobra.

---

## 3. Las cuatro apps: qué entra, qué sale, qué cambia

| App | Entra | Sale | Usa Claude |
|---|---|---|---|
| `test_cases` | PDD / FDD | XLSX de casos de prueba | Sí |
| `pep` | PAP + PDD | DOCX (plan de pruebas) | Sí |
| `aer_test_case` | FDD con Exceptions | XLSX | Sí |
| `msp_qa` | Azure DevOps (API) | Google Sheets (matriz MSP_QA) | **No** |

Las primeras tres son la misma idea: *leer documento → entender con Claude →
generar entregable*. Cambian los prompts, los schemas y el formato de salida.
El esqueleto es idéntico.

**`msp_qa` es la oveja negra y hay que decirlo explícitamente en el KT:**
no lee documentos, no usa Claude. Lee una API (Azure DevOps) y escribe en
otra (Google Sheets). Sigue el mismo patrón de carpetas, pero su complejidad
está en otro lado: parsear texto libre y escribir en una hoja compartida sin
pisar el trabajo manual de nadie.

---

## 4. Dónde se toca cada cosa

Esta es la tabla que el mantenedor va a usar de verdad. Vale la pena que se
la lleve impresa.

| Quiero cambiar… | Toco… |
|---|---|
| Cómo le pido algo a Claude | `apps/<app>/prompts/*.txt` |
| Qué campos espero de vuelta | `apps/<app>/schemas/*.py` |
| El orden de los pasos | `apps/<app>/services/orchestrator.py` |
| Un paso concreto | el módulo de `services/` de ese paso |
| Un mensaje de error al usuario | `apps/<app>/exceptions.py` (`public_message`) |
| El formato del entregable | el service que arma el XLSX/DOCX |
| Estilos / fuentes / cards | `apps/test_cases/static/test_cases/css/test_cases.css` **es la fuente de verdad** — las demás apps reusan sus tokens |
| Una ruta nueva | `apps/<app>/urls.py` + `config/urls.py` |
| Variables de entorno / settings | `config/settings/base.py` y `.env` |

### Sobre el CSS (trampa real, ya nos costó tiempo)

`test_cases.css` define los tokens (`--b-purple`, `--text-xs`, `--btn-h`) y
los componentes (`.pep-alert`, `.pep-plan-table`, `.pep-json-preview`,
`.cta-row`, `.req-item`…). Las otras apps **los reusan, no los redefinen**.

Reglas que hay que transmitir:
- Nunca modificar `test_cases.css` para arreglar otra app. Rompe las cuatro.
- Los overrides van *scopeados* (`.msp-card { … }`), nunca globales.
- `.cta-row` es un grid de `1fr auto 1fr` — espera **tres** hijos. Si pones
  uno solo, el botón se va a la izquierda. La solución es agregar
  `<div class="cta-spacer"></div>` a cada lado, que es lo que hace la app
  original.
- `.card { overflow: hidden }` corta los dropdowns. Si un combobox se ve
  cortado, ese es el culpable.

---

## 5. `msp_qa` en detalle

Es la app más nueva y la que más va a necesitar mantenimiento, porque depende
de datos que escriben humanos a mano.

### Flujo completo

```
1. catalog     → lista proyectos de Azure DevOps (cache 30 min)
2. usuario selecciona varios proyectos (modal multi-select)
3. preview     → por cada proyecto:
     azure_client      → trae la descripción del proyecto
     block_splitter    → parte la descripción en bloques (S1, S2, CR, ÚNICO)
     description_parser→ saca campos del texto libre por alias de etiqueta
     msp_row_builder   → arma la fila de la matriz (calcula horas QA)
   → guarda el resultado en cache (30 min) con un preview_id
4. usuario revisa fila por fila (prev/next) y edita con el lápiz
5. batch_write → sheet_config  → lee la pestaña Config y resuelve columnas
                 matrix_writer → upsert en la matriz
```

### Las tres piezas frágiles

**`description_parser.py` — texto libre.**
La descripción del proyecto en Azure es un campo de texto que escribe una
persona. El parser reconoce ~70 alias para 16 campos (`developer`,
`desenvolvedor`, `desarrollador`, `company`, `cliente`…), normaliza quitando
acentos y pasando a minúsculas. **Cuando alguien escribe una etiqueta nueva,
ese campo sale vacío y nadie se entera.** Por eso existe:

```bash
python manage.py audit_msp_labels
```

Recorre todos los proyectos y reporta las etiquetas que *no* están mapeadas,
ordenadas por frecuencia, más el % de cobertura por campo. **Esto se corre
cada cierto tiempo, no solo cuando algo falla.** Es el mecanismo de defensa
contra la degradación silenciosa.

**`sheet_config.py` — la pestaña Config.**
La configuración vive en una pestaña `Config` dentro de la misma hoja de
Google. Tiene dos bloques, localizados **por su etiqueta**, no por número de
fila: `AJUSTES GENERALES` y `COLUMNAS`.

El mapeo es por **nombre de encabezado**, no por letra de columna. Es decir:
la config dice "el campo `tester` va en la columna cuyo encabezado dice
`TESTER`". Si alguien inserta una columna en medio de la matriz, todo sigue
funcionando solo. Esa fue la razón del cambio y es lo que hay que explicar.

Para verificarla:

```bash
python manage.py check_msp_config
```

Muestra los ajustes leídos, las columnas que resolvió y las columnas de la
matriz que *no* están configuradas.

**`matrix_writer.py` — escribir sin pisar a nadie.**
Dos cosas no negociables:

- **Se escribe celda por celda** (`values.batchUpdate` con rangos
  individuales), nunca un bloque contiguo. Si escribieras un rango completo,
  borrarías las columnas que la gente llena a mano (U–AE).
- **Upsert por ID completo con sufijo** (`AMK.009_S2`, no `AMK.009`). Si el
  ID existe, sobreescribe esa fila; si no, inserta arriba. Cuando se insertan
  N filas nuevas, las filas existentes se desplazan `+N` y las
  actualizaciones se recalculan con ese offset. Esa aritmética es la parte
  más delicada del archivo — está verificada, no la toques sin volver a
  probarla.

### La regla de negocio que siempre preguntan

`HORAS ESTIMADAS` = **20% de las horas totales** que reporta Azure. El
porcentaje no está hardcodeado: sale de `qa_hours_ratio` en la pestaña
Config, y acepta `0.2`, `0,2` o `20%`.

---

## 6. Setup: de repo clonado a sistema corriendo

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
python -m pip install -r requirements.txt
python manage.py runserver
```

**Configuración por defecto:** `config.settings.local`.

**Variables de entorno (`.env`, nunca en el código):**

| Variable | Para qué |
|---|---|
| `AZURE_DEVOPS_ORG_URL` | organización de Azure DevOps |
| `AZURE_DEVOPS_PAT` | Personal Access Token, **solo lectura** |
| `AZURE_DEVOPS_TIMEOUT_SECONDS` | timeout de las llamadas |
| `GOOGLE_CREDENTIALS_FILE` | ruta al `key.json` |
| `MSP_QA_SPREADSHEET_ID` | ID de la hoja de la matriz |
| `MSP_QA_CONFIG_SHEET` | nombre de la pestaña de config (`Config`) |
| `MSP_QA_*_TTL_SECONDS` | TTLs de cache (catálogo, preview, config) |

**`key.json`** es la credencial de la service account de Google. Va en la
raíz del proyecto, **está en `.gitignore`**, y la hoja de cálculo tiene que
estar compartida con el email de esa service account. Sin ese compartir, la
API responde 404 aunque la credencial sea válida.

**El PAT** debe ser de solo lectura, con alcance de organización. Si un
proyecto no aparece en el combobox, casi siempre es permisos del PAT, no que
el proyecto no exista. (Nos pasó: 10 proyectos visibles vs 71 con un PAT más
amplio.)

---

## 7. Trampas conocidas (la sección que ahorra días)

**Azure responde 203 cuando el token es inválido.**
No 401. Devuelve una página de login con status 203. `azure_client.py` lo
trata explícitamente (`HTTP_NON_AUTHORITATIVE = 203`). Si alguien "limpia"
ese caso, los tokens vencidos van a fallar con errores de parseo sin sentido.

**Números con coma de miles.**
`1,040` tiene que leerse como 1040, no como 0.208 al sacarle el 20%.
`extract_first_number()` en `msp_row_builder.py` lo maneja. Hay que saber que
existe antes de "simplificarlo".

**Hueco conocido, sin arreglar todavía:**
si alguien edita la **columna A** de la pestaña Config (el nombre interno del
campo, p.ej. `tester` → `testers`), esa columna **deja de escribirse en
silencio**, porque `row_data.get("testers")` devuelve `None`. El arreglo
pendiente es validar los valores de la columna A contra los 19 campos
conocidos de `MspRow` y detenerse con un mensaje claro. **Vale la pena
mencionarlo en el KT como trabajo pendiente conocido, no esconderlo.**

**Mover la carpeta del proyecto rompe el venv.**
Los `.exe` de `.venv\Scripts\` tienen la ruta del intérprete hardcodeada. Si
mueves el proyecto, `pip install` falla con
`Fatal error in launcher: Unable to create process…`. Solución:
`python -m pip install …` (evita el shim) o recrear el venv.

**CRLF vs LF.**
Los archivos están en CRLF con `core.autocrlf=true`. Si corres git desde una
herramienta que asume LF, vas a ver decenas de archivos "modificados" que no
lo están. En Windows, con VS Code, se ve bien.

**Cuotas de Google Sheets.**
La API tiene límite de peticiones por minuto. Por eso el writer agrupa todo
en **un solo** `batchUpdate` al final en vez de escribir fila por fila. Si
alguien lo "refactoriza" a escrituras individuales, va a chocar con la cuota
en cuanto se manden 20 proyectos.

**Columnas sin automatizar.**
U–AE de la matriz (`TIPO`, `REVISIONES TOTALES`, `TOTAL DE INCIDENCIAS`,
`CAUSA RAÍZ`…) se llenan a mano. Cuatro de ellas podrían venir de Azure, pero
aún no está decidido. Por eso importa tanto la regla de escribir celda por
celda.

---

## 8. Cómo agregar una app nueva

El valor real de entender el patrón es poder replicarlo. La receta:

1. `apps/<nueva>/` con la estructura de la sección 2.
2. Registrar en `config/settings/base.py`:
   `apps.<nueva>.apps.<Nueva>Config` + su logger.
3. `path("<ruta>/", include("apps.<nueva>.urls"))` en `config/urls.py`.
4. Definir los schemas Pydantic **antes** de escribir la lógica. El contrato
   primero.
5. Escribir los prompts como `.txt`.
6. El orchestrator solo ordena; los pasos van en `services/`.
7. Las excepciones heredan del error base de la app, con `code`,
   `public_message` (en inglés), `http_status` y `expose_detail`.
8. El front reusa los tokens y componentes de `test_cases.css`.

---

## 9. Estándar de código

El proyecto sigue la guía interna de buenas prácticas de Python:

- Líneas ≤ 80 caracteres
- Imports agrupados: stdlib / terceros / locales, en ese orden
- Cero credenciales en el código
- Excepciones específicas, nunca `except Exception` a secas
- f-strings
- Comas finales en literales multilínea
- **Identificadores en inglés, docstrings en español**

*(La regla de IDs de trazabilidad de requisitos no aplica a este proyecto.)*

---

## 10. Agenda sugerida (75 min)

| Tiempo | Tema |
|---|---|
| 5 min | Qué es la plataforma y qué problema resuelve |
| **15 min** | **El patrón compartido — la sección que hace o rompe el KT** |
| 10 min | Recorrido por `test_cases` como ejemplo canónico |
| 10 min | Las otras dos apps con Claude: qué cambia y qué no |
| 15 min | `msp_qa`: por qué es distinta, Config, upsert |
| 10 min | Setup, variables de entorno, comandos de diagnóstico |
| 10 min | Trampas conocidas + preguntas |

**Consejo práctico:** una demo en vivo convence más que las diapositivas.
Corre `msp_qa` con dos proyectos y muestra el preview, la edición con el
lápiz y la escritura en la hoja. Quince minutos de eso valen más que
cuarenta de arquitectura en abstracto.

---

## 11. Preguntas que te van a hacer (con respuesta)

**"¿Por qué no hay base de datos?"**
Porque la plataforma transforma, no almacena. Entra un documento, sale otro.
Sin persistencia no hay que decidir quién es dueño del dato ni cuánto vive.
El costo asumido: si el servidor se reinicia a media corrida, se pierde la
corrida.

**"¿Por qué los prompts son archivos de texto?"**
Porque cambian mucho más seguido que el código. Separarlos permite ajustarlos
sin tocar Python y hace que el diff de un cambio de prompt se lea como lo que
es: un cambio de instrucciones, no de lógica.

**"¿Por qué `msp_qa` no usa Claude?"**
Porque no hace falta. El dato de Azure es estructurado o semiestructurado; no
hay ambigüedad que requiera un modelo. Meter un LLM ahí agregaría latencia,
costo y no-determinismo a cambio de nada.

**"¿Qué pasa si alguien mueve una columna de la matriz?"**
Nada. El mapeo es por nombre de encabezado. Lo que *sí* rompe es renombrar el
encabezado sin actualizar la pestaña Config — y en ese caso
`check_msp_config` lo reporta.

**"¿Y si dos personas escriben en la matriz a la vez?"**
Se escribe celda por celda, así que no se pisan columnas ajenas. Pero no hay
locking: si dos corridas insertan filas al mismo tiempo, el offset de una
puede quedar mal. En la práctica no pasa porque la usa una persona a la vez.
Es una limitación honesta que conviene decir en voz alta.
