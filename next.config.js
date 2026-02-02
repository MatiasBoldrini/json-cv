/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    // Excluir estos paquetes del bundling de Next.js
    // para que mantengan sus paths internos correctos
    serverComponentsExternalPackages: [
      "@sparticuz/chromium",
      "puppeteer-core"
    ],
    // Incluir archivos estáticos necesarios para el PDF
    outputFileTracingIncludes: {
      "/api/generate-pdf": [
        "./style.css",
        "./resume.hbs",
        "./node_modules/@sparticuz/chromium/**/*"
      ]
    }
  },
  webpack(config) {
    config.module.rules.push(
      {
        test: /\.hbs$/,
        type: "asset/source"
      },
      {
        test: /\.css$/,
        resourceQuery: /raw/,
        type: "asset/source"
      }
    );
    return config;
  }
};

module.exports = nextConfig;
