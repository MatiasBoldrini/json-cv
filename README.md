# JSON-CV

Este proyecto es un tema que no encontré disponible en JSON Resume y por eso lo armé: necesitaba un CV de una sola página, fácil de leer por reclutadores, optimizado para ATS y con una estructura clara para editarlo sin fricción.

La gracia es que también está optimizado para que una IA pueda consultar este servicio y generar mi resumen a partir de un prompt en español, sin tener que volcar todo el JSON en el README porque eso ya vive dentro del prompt de `custom-gem-prompt.md`.

A modo de referencia, así se vería una solicitud tipo curl para interactuar con una IA y generar el resumen, sin mostrar el JSON completo:

curl -X POST https://cv-matias-boldrini.vercel.app/api/generate-pdf -H "Content-Type: application/json" -d @resume.json

Si querés modificar el custom gem, el prompt de este se encuentra en el archivo custom-gem-prompt.md