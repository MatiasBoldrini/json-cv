"use client";

import { useState } from "react";
import EditableText from "./EditableText";
import PhotoUploader from "./PhotoUploader";
import JSONImporter from "./JSONImporter";
import { getDefaultResume } from "../lib/default-resume";
import { normalizeResume } from "../lib/normalize-resume";

const DEFAULT_LABELS = {
  work: "EXPERIENCIA LABORAL",
  education: "FORMACIÓN ACADÉMICA",
  certificates: "CERTIFICACIONES",
  skills: "CONOCIMIENTOS",
  languages: "IDIOMAS",
  volunteer: "COMUNIDAD",
  projects: "PROYECTOS",
  email: "Email",
  phone: "Tel",
  location: "Ubicación"
};

function setIn(obj, path, value) {
  if (!path.length) return value;
  const clone = Array.isArray(obj) ? [...obj] : { ...obj };
  let current = clone;
  for (let i = 0; i < path.length - 1; i += 1) {
    const key = path[i];
    const next = current[key];
    const nextClone = Array.isArray(next) ? [...next] : { ...next };
    current[key] = nextClone;
    current = nextClone;
  }
  current[path[path.length - 1]] = value;
  return clone;
}

export default function ResumeEditor() {
  const [resume, setResume] = useState(() => normalizeResume(getDefaultResume()));
  const [labels, setLabels] = useState(DEFAULT_LABELS);
  const [status, setStatus] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);

  const handleImportJson = (data) => {
    setResume(normalizeResume(data));
  };

  const updateResume = (path, value) => {
    setResume((prev) => setIn(prev, path, value));
  };

  const updateResumeMulti = (updates) => {
    setResume((prev) =>
      updates.reduce((next, update) => setIn(next, update.path, update.value), prev)
    );
  };

  const updateLabel = (key, value) => {
    setLabels((prev) => ({ ...prev, [key]: value }));
  };

  const handleGeneratePdf = async () => {
    setIsGenerating(true);
    setStatus("Generando PDF...");
    try {
      const response = await fetch("/api/generate-pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(resume)
      });

      if (!response.ok) {
        throw new Error("Error al generar PDF");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      const safeName = resume?.basics?.name
        ? resume.basics.name.replace(/[^a-z0-9]/gi, "_").toLowerCase()
        : "cv";
      link.href = url;
      link.download = `${safeName}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setStatus("PDF descargado.");
    } catch (error) {
      setStatus("No se pudo generar el PDF.");
    } finally {
      setIsGenerating(false);
    }
  };

  const basics = resume.basics || {};
  const profileMeta = basics.meta || [];
  const profiles = basics.profiles || [];

  return (
    <div>
      <div className="toolbar">
        <JSONImporter onImport={handleImportJson} />
        <button
          type="button"
          className="toolbarButton"
          onClick={handleGeneratePdf}
          disabled={isGenerating}
        >
          {isGenerating ? "Generando PDF..." : "Descargar PDF"}
        </button>
        {status ? <span className="statusText">{status}</span> : null}
      </div>

      <div id="resume">
        <div id="header">
          <div id="headerLeft">
            <div id="photoBlock">
              <PhotoUploader
                value={basics.image}
                onChange={(value) => updateResume(["basics", "image"], value)}
              />
            </div>
            <div id="headerIdentity">
              <EditableText
                value={basics.name}
                onChange={(value) => updateResume(["basics", "name"], value)}
                className="name"
                tagName="h1"
              />
              <EditableText
                value={basics.label}
                onChange={(value) => updateResume(["basics", "label"], value)}
                className="label"
                tagName="div"
              />
              <div className="metaInfo">
                {profileMeta.map((item, index) => (
                  <span key={`meta-${index}`} className="metaItem">
                    <EditableText
                      value={item}
                      onChange={(value) =>
                        updateResume(["basics", "meta", index], value)
                      }
                      className=""
                    />
                    {index < profileMeta.length - 1 ? (
                      <span className="metaDivider">|</span>
                    ) : null}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div id="headerRight">
            <EditableText
              value={basics.summary}
              onChange={(value) => updateResume(["basics", "summary"], value)}
              className="summary"
              tagName="p"
            />
          </div>
        </div>

        <div id="contactBlock">
          {basics.email ? (
            <div className="contactItem">
              <EditableText
                value={labels.email}
                onChange={(value) => updateLabel("email", value)}
                className="contactLabel"
                tagName="span"
              />
              <span className="contactValue">
                <EditableText
                  value={basics.email}
                  onChange={(value) => updateResume(["basics", "email"], value)}
                  className=""
                  tagName="span"
                />
              </span>
            </div>
          ) : null}
          {basics.phone ? (
            <div className="contactItem">
              <EditableText
                value={labels.phone}
                onChange={(value) => updateLabel("phone", value)}
                className="contactLabel"
                tagName="span"
              />
              <span className="contactValue">
                <EditableText
                  value={basics.phone}
                  onChange={(value) => updateResume(["basics", "phone"], value)}
                  className=""
                  tagName="span"
                />
              </span>
            </div>
          ) : null}
          {basics.location ? (
            <div className="contactItem">
              <EditableText
                value={labels.location}
                onChange={(value) => updateLabel("location", value)}
                className="contactLabel"
                tagName="span"
              />
              <span className="contactValue">
                <EditableText
                  value={`${basics.location.city || ""}${basics.location.region ? `, ${basics.location.region}` : ""}`}
                  onChange={(value) => {
                    const [city, region] = value.split(",").map((s) => s.trim());
                    updateResumeMulti([
                      { path: ["basics", "location", "city"], value: city || "" },
                      { path: ["basics", "location", "region"], value: region || "" }
                    ]);
                  }}
                  className=""
                  tagName="span"
                />
              </span>
            </div>
          ) : null}
          {profiles.map((profile, index) => (
            <div className="contactItem" key={`profile-${index}`}>
              <EditableText
                value={profile.network}
                onChange={(value) => updateResume(["basics", "profiles", index, "network"], value)}
                className="contactLabel"
                tagName="span"
              />
              <span className="contactValue">
                <EditableText
                  value={profile.username || "Ver perfil"}
                  onChange={(value) =>
                    updateResume(["basics", "profiles", index, "username"], value)
                  }
                  className=""
                  tagName="span"
                />
              </span>
            </div>
          ))}
        </div>
        <div className="sectionLine" />

        {resume.work.length ? (
          <>
            <div id="workBlock" className="sectionBlock">
              <div className="sectionName">
                <EditableText
                  value={labels.work}
                  onChange={(value) => updateLabel("work", value)}
                  className="sectionTitleEditable"
                />
              </div>
              <div className="sectionContent">
                {resume.work.map((job, index) => (
                  <div className="jobBlock" key={`job-${index}`}>
                    <div className="blockHeader">
                      <EditableText
                        value={job.position}
                        onChange={(value) =>
                          updateResume(["work", index, "position"], value)
                        }
                        className="title"
                        tagName="span"
                      />
                      <EditableText
                        value={`${job.startDate || ""}${job.endDate ? ` — ${job.endDate}` : " — Actualidad"}`}
                        onChange={(value) => {
                          const [start, end] = value.split("—").map((s) => s.trim());
                          updateResumeMulti([
                            { path: ["work", index, "startDate"], value: start || "" },
                            { path: ["work", index, "endDate"], value: end || "" }
                          ]);
                        }}
                        className="date"
                        tagName="span"
                      />
                    </div>
                    <EditableText
                      value={job.name}
                      onChange={(value) => updateResume(["work", index, "name"], value)}
                      className="company"
                      tagName="div"
                    />
                    {job.highlights?.length ? (
                      <ul className="highlights">
                        {job.highlights.map((highlight, highlightIndex) => (
                          <EditableText
                            key={`job-${index}-highlight-${highlightIndex}`}
                            value={highlight}
                            onChange={(value) =>
                              updateResume(["work", index, "highlights", highlightIndex], value)
                            }
                            className=""
                            tagName="li"
                          />
                        ))}
                      </ul>
                    ) : null}
                    {index < resume.work.length - 1 ? <div className="separator" /> : null}
                  </div>
                ))}
              </div>
            </div>
            <div className="sectionLine" />
          </>
        ) : null}

        {resume.education.length ? (
          <>
            <div id="education" className="sectionBlock">
              <div className="sectionName">
                <EditableText
                  value={labels.education}
                  onChange={(value) => updateLabel("education", value)}
                  className="sectionTitleEditable"
                />
              </div>
              <div className="sectionContent">
                {resume.education.map((edu, index) => (
                  <div className="educationBlock" key={`edu-${index}`}>
                    <div className="blockHeader">
                      <EditableText
                        value={`${edu.studyType ? `${edu.studyType} - ` : ""}${edu.area || ""}`}
                        onChange={(value) => {
                          const [studyType, area] = value.split("-").map((s) => s.trim());
                          updateResumeMulti([
                            { path: ["education", index, "studyType"], value: studyType || "" },
                            { path: ["education", index, "area"], value: area || "" }
                          ]);
                        }}
                        className="title"
                        tagName="span"
                      />
                      <EditableText
                        value={`${edu.startDate || ""}${edu.endDate ? ` — ${edu.endDate}` : " — Actualidad"}`}
                        onChange={(value) => {
                          const [start, end] = value.split("—").map((s) => s.trim());
                          updateResumeMulti([
                            { path: ["education", index, "startDate"], value: start || "" },
                            { path: ["education", index, "endDate"], value: end || "" }
                          ]);
                        }}
                        className="date"
                        tagName="span"
                      />
                    </div>
                    <EditableText
                      value={edu.institution}
                      onChange={(value) =>
                        updateResume(["education", index, "institution"], value)
                      }
                      className="institution"
                      tagName="div"
                    />
                    <EditableText
                      value={edu.score}
                      onChange={(value) => updateResume(["education", index, "score"], value)}
                      className="score"
                      tagName="div"
                    />
                    {index < resume.education.length - 1 ? (
                      <div className="separator" />
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
            <div className="sectionLine" />
          </>
        ) : null}

        {resume.certificates.length ? (
          <>
            <div id="certificates" className="sectionBlock">
              <div className="sectionName">
                <EditableText
                  value={labels.certificates}
                  onChange={(value) => updateLabel("certificates", value)}
                  className="sectionTitleEditable"
                />
              </div>
              <div className="sectionContent">
                {resume.certificates.map((cert, index) => (
                  <div className="certBlock" key={`cert-${index}`}>
                    <EditableText
                      value={cert.name}
                      onChange={(value) => updateResume(["certificates", index, "name"], value)}
                      className="title"
                      tagName="span"
                    />
                    <EditableText
                      value={cert.date}
                      onChange={(value) => updateResume(["certificates", index, "date"], value)}
                      className="date"
                      tagName="span"
                    />
                    <EditableText
                      value={cert.issuer}
                      onChange={(value) =>
                        updateResume(["certificates", index, "issuer"], value)
                      }
                      className="issuer"
                      tagName="div"
                    />
                    {index < resume.certificates.length - 1 ? (
                      <div className="separator" />
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
            <div className="sectionLine" />
          </>
        ) : null}

        {resume.skills.length ? (
          <>
            <div id="skills" className="sectionBlock">
              <div className="sectionName">
                <EditableText
                  value={labels.skills}
                  onChange={(value) => updateLabel("skills", value)}
                  className="sectionTitleEditable"
                />
              </div>
              <div className="sectionContent">
                {resume.skills.map((skill, index) => (
                  <div className="skillBlock" key={`skill-${index}`}>
                    <EditableText
                      value={skill.name}
                      onChange={(value) => updateResume(["skills", index, "name"], value)}
                      className="skillName"
                      tagName="span"
                    />
                    <span className="skillKeywords">
                      {skill.keywords?.map((keyword, keywordIndex) => (
                        <span key={`skill-${index}-kw-${keywordIndex}`}>
                          <EditableText
                            value={keyword}
                            onChange={(value) =>
                              updateResume(["skills", index, "keywords", keywordIndex], value)
                            }
                            className=""
                            tagName="span"
                          />
                          {keywordIndex < skill.keywords.length - 1 ? ", " : ""}
                        </span>
                      ))}
                    </span>
                  </div>
                ))}
              </div>
            </div>
            <div className="sectionLine" />
          </>
        ) : null}

        {resume.languages.length ? (
          <>
            <div id="languages" className="sectionBlock">
              <div className="sectionName">
                <EditableText
                  value={labels.languages}
                  onChange={(value) => updateLabel("languages", value)}
                  className="sectionTitleEditable"
                />
              </div>
              <div className="sectionContent">
                {resume.languages.map((lang, index) => (
                  <span key={`lang-${index}`}>
                    <EditableText
                      value={lang.language}
                      onChange={(value) =>
                        updateResume(["languages", index, "language"], value)
                      }
                      className="language"
                      tagName="span"
                    />
                    <EditableText
                      value={lang.fluency}
                      onChange={(value) =>
                        updateResume(["languages", index, "fluency"], value)
                      }
                      className="fluency"
                      tagName="span"
                    />
                    {index < resume.languages.length - 1 ? (
                      <span className="langDivider"> | </span>
                    ) : null}
                  </span>
                ))}
              </div>
            </div>
            <div className="sectionLine" />
          </>
        ) : null}

        {resume.volunteer.length ? (
          <>
            <div id="volunteer" className="sectionBlock">
              <div className="sectionName">
                <EditableText
                  value={labels.volunteer}
                  onChange={(value) => updateLabel("volunteer", value)}
                  className="sectionTitleEditable"
                />
              </div>
              <div className="sectionContent">
                {resume.volunteer.map((item, index) => (
                  <div className="volunteerBlock" key={`vol-${index}`}>
                    <div className="blockHeader">
                      <EditableText
                        value={item.position}
                        onChange={(value) =>
                          updateResume(["volunteer", index, "position"], value)
                        }
                        className="title"
                        tagName="span"
                      />
                      <EditableText
                        value={`${item.startDate || ""}${item.endDate ? ` — ${item.endDate}` : " — Actualidad"}`}
                        onChange={(value) => {
                          const [start, end] = value.split("—").map((s) => s.trim());
                          updateResumeMulti([
                            { path: ["volunteer", index, "startDate"], value: start || "" },
                            { path: ["volunteer", index, "endDate"], value: end || "" }
                          ]);
                        }}
                        className="date"
                        tagName="span"
                      />
                    </div>
                    <EditableText
                      value={item.organization}
                      onChange={(value) =>
                        updateResume(["volunteer", index, "organization"], value)
                      }
                      className="organization"
                      tagName="div"
                    />
                    <EditableText
                      value={item.summary}
                      onChange={(value) =>
                        updateResume(["volunteer", index, "summary"], value)
                      }
                      className="volunteerSummary"
                      tagName="div"
                    />
                    {index < resume.volunteer.length - 1 ? (
                      <div className="separator" />
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
            <div className="sectionLine" />
          </>
        ) : null}

        {resume.projects.length ? (
          <>
            <div id="projects" className="sectionBlock">
              <div className="sectionName">
                <EditableText
                  value={labels.projects}
                  onChange={(value) => updateLabel("projects", value)}
                  className="sectionTitleEditable"
                />
              </div>
              <div className="sectionContent">
                {resume.projects.map((project, index) => (
                  <div className="projectBlock" key={`project-${index}`}>
                    <div className="blockHeader">
                      <EditableText
                        value={project.name}
                        onChange={(value) =>
                          updateResume(["projects", index, "name"], value)
                        }
                        className="title"
                        tagName="span"
                      />
                      <EditableText
                        value={`${project.startDate || ""}${project.endDate ? ` — ${project.endDate}` : ""}`}
                        onChange={(value) => {
                          const [start, end] = value.split("—").map((s) => s.trim());
                          updateResumeMulti([
                            { path: ["projects", index, "startDate"], value: start || "" },
                            { path: ["projects", index, "endDate"], value: end || "" }
                          ]);
                        }}
                        className="date"
                        tagName="span"
                      />
                    </div>
                    <EditableText
                      value={project.url}
                      onChange={(value) =>
                        updateResume(["projects", index, "url"], value)
                      }
                      className="projectUrl"
                      tagName="div"
                    />
                    <EditableText
                      value={project.description}
                      onChange={(value) =>
                        updateResume(["projects", index, "description"], value)
                      }
                      className="projectDesc"
                      tagName="div"
                    />
                    {project.highlights?.length ? (
                      <ul className="highlights">
                        {project.highlights.map((highlight, highlightIndex) => (
                          <EditableText
                            key={`project-${index}-highlight-${highlightIndex}`}
                            value={highlight}
                            onChange={(value) =>
                              updateResume([
                                "projects",
                                index,
                                "highlights",
                                highlightIndex
                              ], value)
                            }
                            className=""
                            tagName="li"
                          />
                        ))}
                      </ul>
                    ) : null}
                    {project.keywords?.length ? (
                      <div className="projectTech">
                        {project.keywords.map((keyword, keywordIndex) => (
                          <span key={`project-${index}-kw-${keywordIndex}`}>
                            <EditableText
                              value={keyword}
                              onChange={(value) =>
                                updateResume([
                                  "projects",
                                  index,
                                  "keywords",
                                  keywordIndex
                                ], value)
                              }
                              className=""
                              tagName="span"
                            />
                            {keywordIndex < project.keywords.length - 1 ? ", " : ""}
                          </span>
                        ))}
                      </div>
                    ) : null}
                    {index < resume.projects.length - 1 ? (
                      <div className="separator" />
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
