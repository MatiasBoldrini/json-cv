const DEFAULT_ARRAYS = [
  "work",
  "volunteer",
  "education",
  "certificates",
  "skills",
  "languages",
  "projects"
];

export function normalizeResume(input) {
  const resume = input ? JSON.parse(JSON.stringify(input)) : {};
  resume.basics = resume.basics || {};
  resume.basics.meta = Array.isArray(resume.basics.meta) ? resume.basics.meta : [];
  resume.basics.profiles = Array.isArray(resume.basics.profiles)
    ? resume.basics.profiles
    : [];

  DEFAULT_ARRAYS.forEach((key) => {
    if (!Array.isArray(resume[key])) {
      resume[key] = [];
    }
  });

  resume.work = resume.work.map((item) => ({
    highlights: [],
    ...item,
    highlights: Array.isArray(item?.highlights) ? item.highlights : []
  }));

  resume.education = resume.education.map((item) => ({
    courses: [],
    ...item,
    courses: Array.isArray(item?.courses) ? item.courses : []
  }));

  resume.certificates = resume.certificates.map((item) => ({
    ...item
  }));

  resume.skills = resume.skills.map((item) => ({
    keywords: [],
    ...item,
    keywords: Array.isArray(item?.keywords) ? item.keywords : []
  }));

  resume.languages = resume.languages.map((item) => ({
    ...item
  }));

  resume.volunteer = resume.volunteer.map((item) => ({
    ...item
  }));

  resume.projects = resume.projects.map((item) => ({
    keywords: [],
    highlights: [],
    ...item,
    keywords: Array.isArray(item?.keywords) ? item.keywords : [],
    highlights: Array.isArray(item?.highlights) ? item.highlights : []
  }));

  return resume;
}
