import Handlebars from "handlebars";
import { normalizeResume } from "./normalize-resume";
import css from "../style.css?raw";
import template from "../resume.hbs";

export function renderResumeHtml(resumeInput) {
  const resume = normalizeResume(resumeInput);
  return Handlebars.compile(template)({
    css,
    resume
  });
}
