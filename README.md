# my-resume-theme

Tema personalizado de CV en una sola página basado en JSON Resume.

## Uso (local)

1. Instalar dependencias:

```
npm install
```

2. Levantar el editor:

```
npm run dev
```

3. Generar el PDF desde script local:

```
npm run generate
```

El archivo generado queda en `CV-matias-boldrini.pdf`.

## API para PDF (Vercel)

```
POST /api/generate-pdf
Content-Type: application/json
```

Ejemplo con curl:

```
curl -X POST https://tu-app.vercel.app/api/generate-pdf \
  -H "Content-Type: application/json" \
  -d @resume.json \
  -o cv.pdf
```

El campo `basics.image` acepta URL o base64.

## Archivos clave

- `resume.json`: contenido del CV.
- `resume.hbs`: template del CV.
- `style.css`: estilos del template.
- `generate-pdf.js`: script para generar el PDF.
