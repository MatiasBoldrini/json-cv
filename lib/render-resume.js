import fs from "fs";
import path from "path";
import Handlebars from "handlebars";
import { normalizeResume } from "./normalize-resume";

export function renderResumeHtml(resumeInput) {
  const resume = normalizeResume(resumeInput);
  const baseDir = process.cwd();
  const cssPath = path.join(baseDir, "style.css");
  const templatePath = path.join(baseDir, "resume.hbs");
  const css = fs.readFileSync(cssPath, "utf-8");
  const tpl = fs.readFileSync(templatePath, "utf-8");

  return Handlebars.compile(tpl)({
    css,
    resume
  });
}
