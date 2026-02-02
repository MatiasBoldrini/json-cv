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

export function renderResumeHtml(resumeInput) {
  const resume = normalizeResume(resumeInput);
  const css = readTextFile("style.css");
  const tpl = readTextFile("resume.hbs");

  return Handlebars.compile(tpl)({
    css,
    resume
  });
}
