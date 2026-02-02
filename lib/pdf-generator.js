import fs from "fs";
import path from "path";
import chromium from "@sparticuz/chromium";
import puppeteer from "puppeteer-core";

export async function generatePdfBuffer(html) {
  const chromiumBinPath = path.join(
    process.cwd(),
    "node_modules",
    "@sparticuz",
    "chromium",
    "bin"
  );
  const executablePath = await chromium.executablePath(
    fs.existsSync(chromiumBinPath) ? chromiumBinPath : undefined
  );

  const browser = await puppeteer.launch({
    args: chromium.args,
    executablePath,
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
