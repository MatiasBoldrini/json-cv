import fs from "fs";
import Handlebars from "handlebars";
import { normalizeResume } from "./normalize-resume";

const cssPath = new URL("../style.css", import.meta.url);
const templatePath = new URL("../resume.hbs", import.meta.url);

export function renderResumeHtml(resumeInput) {
  const resume = normalizeResume(resumeInput);

  const css = fs.readFileSync(cssPath, "utf-8");
  const tpl = fs.readFileSync(templatePath, "utf-8");

  return Handlebars.compile(tpl)({
    css,
    resume
  });
}
