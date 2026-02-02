import fs from "fs";
import path from "path";
import Handlebars from "handlebars";
import { normalizeResume } from "./normalize-resume";

function getBaseDir() {
  // En Vercel, los archivos están en /var/task
  if (process.env.VERCEL) {
    return "/var/task";
  }
  // En desarrollo, usar process.cwd()
  return process.cwd();
}

export function renderResumeHtml(resumeInput) {
  const resume = normalizeResume(resumeInput);

  const baseDir = getBaseDir();
  const cssPath = path.join(baseDir, "style.css");
  const templatePath = path.join(baseDir, "resume.hbs");

  const css = fs.readFileSync(cssPath, "utf-8");
  const tpl = fs.readFileSync(templatePath, "utf-8");

  return Handlebars.compile(tpl)({
    css,
    resume
  });
}
