import chromium from "@sparticuz/chromium";
import puppeteer from "puppeteer-core";

export async function generatePdfBuffer(html) {
  // Configuración para @sparticuz/chromium en Vercel
  chromium.setHeadlessMode = true;
  chromium.setGraphicsMode = false;

  const browser = await puppeteer.launch({
    args: chromium.args,
    defaultViewport: chromium.defaultViewport,
    executablePath: await chromium.executablePath(),
    headless: chromium.headless
  });

  try {
    const page = await browser.newPage();
    await page.setContent(html, { waitUntil: "networkidle0" });
    const pdfBuffer = await page.pdf({
      format: "A4",
      printBackground: true,
      margin: {
        top: "10mm",
        right: "10mm",
        bottom: "10mm",
        left: "10mm"
      }
    });
    return pdfBuffer;
  } finally {
    await browser.close();
  }
}
