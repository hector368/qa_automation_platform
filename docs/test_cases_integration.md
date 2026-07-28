# Integración — Test Case Generator

## Descripción

`apps.test_cases` es una aplicación Django autocontenida para:

- Recibir documentos PDF o DOCX.
- Extraer su contenido.
- Detectar el ID del proyecto.
- Identificar y segmentar requerimientos funcionales.
- Permitir la selección de requerimientos.
- Generar casos de prueba mediante Claude.
- Producir un CSV compatible con Azure DevOps.
- Transmitir el progreso mediante NDJSON.
- Almacenar temporalmente el resultado para descarga.

La aplicación no depende de `apps.pep`.

---

## Requisitos

- Python 3.12.
- Django.
- Anthropic SDK.
- Pydantic.
- PyMuPDF.
- python-docx.
- python-dotenv.

---

## Instalación

Copiar la carpeta:

```text
apps/test_cases/