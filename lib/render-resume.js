import fs from "fs";
import Handlebars from "handlebars";
import { normalizeResume } from "./normalize-resume";

export function renderResumeHtml(resumeInput) {
  const resume = normalizeResume(resumeInput);
  const cssPath = new URL("../style.css", import.meta.url);
  const templatePath = new URL("../resume.hbs", import.meta.url);
  const css = fs.readFileSync(cssPath, "utf-8");
  const tpl = fs.readFileSync(templatePath, "utf-8");

  return Handlebars.compile(tpl)({
    css,
    resume
  });
}
