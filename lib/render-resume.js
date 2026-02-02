import fs from "fs";
import path from "path";
import Handlebars from "handlebars";
import { normalizeResume } from "./normalize-resume";

export function renderResumeHtml(resumeInput) {
  const resume = normalizeResume(resumeInput);
  const rootPath = process.cwd();
  const css = fs.readFileSync(path.join(rootPath, "style.css"), "utf-8");
  const tpl = fs.readFileSync(path.join(rootPath, "resume.hbs"), "utf-8");

  return Handlebars.compile(tpl)({
    css,
    resume
  });
}
