import resume from "../resume.json";

export function getDefaultResume() {
  return JSON.parse(JSON.stringify(resume));
}
