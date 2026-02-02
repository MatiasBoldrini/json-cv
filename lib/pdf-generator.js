import chromium from "@sparticuz/chromium";
import puppeteerCore from "puppeteer-core";

const CHROMIUM_PACK_URL =
  process.env.CHROMIUM_PACK_URL ||
  "https://github.com/Sparticuz/chromium/releases/download/v122.0.0/chromium-v122.0.0-pack.tar";

async function getPuppeteer() {
  if (process.env.VERCEL) {
    return puppeteerCore;
  }

  try {
    const puppeteer = await import("puppeteer");
    return puppeteer.default ?? puppeteer;
  } catch {
    return puppeteerCore;
  }
}

export async function generatePdfBuffer(html) {
  const puppeteer = await getPuppeteer();

  // Configuración para @sparticuz/chromium en Vercel
  chromium.setHeadlessMode = true;
  chromium.setGraphicsMode = false;

  const isVercel = !!process.env.VERCEL;
  const executablePath = isVercel
    ? await chromium.executablePath(CHROMIUM_PACK_URL)
    : undefined;

  const launchOptions = {
    args: isVercel
      ? puppeteer.defaultArgs({ args: chromium.args, headless: "shell" })
      : puppeteer.defaultArgs(),
    defaultViewport: chromium.defaultViewport,
    headless: isVercel ? "shell" : "new"
  };

  if (executablePath) {
    launchOptions.executablePath = executablePath;
  }

  const browser = await puppeteer.launch(launchOptions);

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
