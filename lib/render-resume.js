import fs from "fs";
import path from "path";
import Handlebars from "handlebars";
import { fileURLToPath } from "url";
import { normalizeResume } from "./normalize-resume";

export function renderResumeHtml(resumeInput) {
  const resume = normalizeResume(resumeInput);
  const baseDir = path.dirname(fileURLToPath(import.meta.url));
  const cssPath = path.join(baseDir, "../style.css");
  const templatePath = path.join(baseDir, "../resume.hbs");
  const css = fs.readFileSync(cssPath, "utf-8");
  const tpl = fs.readFileSync(templatePath, "utf-8");

  return Handlebars.compile(tpl)({
    css,
    resume
  });
}
