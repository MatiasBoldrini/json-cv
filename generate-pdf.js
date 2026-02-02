let puppeteer = null;
let chromium = null;
try {
  puppeteer = require('puppeteer');
} catch (error) {
  puppeteer = require('puppeteer-core');
  chromium = require('@sparticuz/chromium');
}
const theme = require('./index.js');
const resume = require('./resume.json');
const fs = require('fs');
const path = require('path');

async function generatePDF() {
  console.log('Generando HTML...');
  const html = theme.render(resume);
  const htmlPath = path.join(__dirname, 'temp-resume.html');
  fs.writeFileSync(htmlPath, html);

  console.log('Iniciando Chrome...');
  const launchOptions = chromium
    ? {
      args: chromium.args,
      executablePath: await chromium.executablePath(),
      headless: chromium.headless
    }
    : {
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    };

  const browser = await puppeteer.launch(launchOptions);

  const page = await browser.newPage();

  // Cargar el HTML
  await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0' });

  console.log('Generando PDF...');
  const pdfPath = path.join(__dirname, 'CV-matias-boldrini.pdf');
  await page.pdf({
    path: pdfPath,
    format: 'A4',
    printBackground: true,
    margin: {
      top: '10mm',
      right: '10mm',
      bottom: '10mm',
      left: '10mm'
    }
  });

  await browser.close();

  // Limpiar archivo temporal
  fs.unlinkSync(htmlPath);

  console.log(`PDF generado: ${pdfPath}`);
}

generatePDF().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
