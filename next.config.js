/** @type {import('next').NextConfig} */
const nextConfig = {
  // Excluir estos paquetes del bundling de Next.js
  // para que mantengan sus paths internos correctos
  serverExternalPackages: [
    "@sparticuz/chromium",
    "puppeteer-core"
  ],

  // Incluir archivos estáticos necesarios para el PDF
  outputFileTracingIncludes: {
    "/app/api/generate-pdf/route": [
      "./style.css",
      "./resume.hbs",
      "./node_modules/@sparticuz/chromium/**/*"
    ]
  }
};

module.exports = nextConfig;
