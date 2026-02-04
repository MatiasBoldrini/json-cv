import fs from "fs";
import path from "path";
import Handlebars from "handlebars";
import { normalizeResume } from "./normalize-resume";

function readTextFile(fileName) {
  const cwdPath = path.join(process.cwd(), fileName);
  if (fs.existsSync(cwdPath)) {
    return fs.readFileSync(cwdPath, "utf-8");
  }

  const varTaskPath = path.join("/var/task", fileName);
  if (fs.existsSync(varTaskPath)) {
    return fs.readFileSync(varTaskPath, "utf-8");
  }

  return fs.readFileSync(fileName, "utf-8");
}

function imageToBase64(imagePath) {
  try {
    // Intentar con la ruta del directorio actual
    const cwdPath = path.join(process.cwd(), imagePath);
    if (fs.existsSync(cwdPath)) {
      const imageBuffer = fs.readFileSync(cwdPath);
      const ext = path.extname(imagePath).toLowerCase();
      const mimeType = ext === '.png' ? 'image/png' :
        ext === '.jpg' || ext === '.jpeg' ? 'image/jpeg' :
          ext === '.gif' ? 'image/gif' : 'image/jpeg';
      return `data:${mimeType};base64,${imageBuffer.toString('base64')}`;
    }

    // Intentar con /var/task (para Vercel/Lambda)
    const varTaskPath = path.join("/var/task", imagePath);
    if (fs.existsSync(varTaskPath)) {
      const imageBuffer = fs.readFileSync(varTaskPath);
      const ext = path.extname(imagePath).toLowerCase();
      const mimeType = ext === '.png' ? 'image/png' :
        ext === '.jpg' || ext === '.jpeg' ? 'image/jpeg' :
          ext === '.gif' ? 'image/gif' : 'image/jpeg';
      return `data:${mimeType};base64,${imageBuffer.toString('base64')}`;
    }

    // Intentar con la ruta directa
    if (fs.existsSync(imagePath)) {
      const imageBuffer = fs.readFileSync(imagePath);
      const ext = path.extname(imagePath).toLowerCase();
      const mimeType = ext === '.png' ? 'image/png' :
        ext === '.jpg' || ext === '.jpeg' ? 'image/jpeg' :
          ext === '.gif' ? 'image/gif' : 'image/jpeg';
      return `data:${mimeType};base64,${imageBuffer.toString('base64')}`;
    }
  } catch (error) {
    console.error(`Error convirtiendo imagen a base64: ${imagePath}`, error);
  }
  return null;
}

export function renderResumeHtml(resumeInput) {
  const resume = normalizeResume(resumeInput);

  // Convertir imagen local a base64 si no es una URL
  if (resume.basics?.image && !resume.basics.image.startsWith('http')) {
    const base64Image = imageToBase64(resume.basics.image);
    if (base64Image) {
      resume.basics.image = base64Image;
    }
  }

  const css = readTextFile("style.css");
  const tpl = readTextFile("resume.hbs");

  return Handlebars.compile(tpl)({
    css,
    resume
  });
}
