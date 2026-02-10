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
    const normalizedPath = imagePath.startsWith("/")
      ? imagePath.slice(1)
      : imagePath;
    const publicRelativePath = normalizedPath.startsWith("public/")
      ? normalizedPath
      : path.join("public", normalizedPath);
    const ext = path.extname(normalizedPath).toLowerCase();
    const mimeType = ext === ".png"
      ? "image/png"
      : ext === ".jpg" || ext === ".jpeg"
        ? "image/jpeg"
        : ext === ".gif"
          ? "image/gif"
          : "image/jpeg";

    const candidatePaths = [
      path.join(process.cwd(), normalizedPath),
      path.join(process.cwd(), publicRelativePath),
      path.join("/var/task", normalizedPath),
      path.join("/var/task", publicRelativePath),
      imagePath
    ];

    for (const candidatePath of candidatePaths) {
      if (fs.existsSync(candidatePath)) {
        const imageBuffer = fs.readFileSync(candidatePath);
        return `data:${mimeType};base64,${imageBuffer.toString("base64")}`;
      }
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
