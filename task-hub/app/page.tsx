"use client";

import {
  ChangeEvent,
  FormEvent,
  KeyboardEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

type CareerTask = {
  id: string;
  date: string;
  task: string;
  project: string;
  technologies: string[];
  impact: string;
  includeInResume: boolean;
  createdAt: string;
};

type TaskDraft = {
  date: string;
  task: string;
  project: string;
  technologyInput: string;
  technologies: string[];
  impact: string;
  includeInResume: boolean;
};

const STORAGE_KEY = "job-agent-career-tasks-v1";

const emptyDraft = (): TaskDraft => ({
  date: new Date().toISOString().slice(0, 10),
  task: "",
  project: "",
  technologyInput: "",
  technologies: [],
  impact: "",
  includeInResume: true,
});

function createId() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function isCareerTask(value: unknown): value is CareerTask {
  if (!value || typeof value !== "object") return false;
  const item = value as Record<string, unknown>;
  return (
    typeof item.id === "string" &&
    typeof item.date === "string" &&
    typeof item.task === "string" &&
    typeof item.project === "string" &&
    Array.isArray(item.technologies) &&
    item.technologies.every((skill) => typeof skill === "string") &&
    typeof item.impact === "string" &&
    typeof item.includeInResume === "boolean" &&
    typeof item.createdAt === "string"
  );
}

function formatDate(value: string) {
  const parsed = new Date(`${value}T00:00:00`);
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(parsed);
}

function downloadFile(name: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function buildTaskLog(tasks: CareerTask[]) {
  const included = tasks.filter((task) => task.includeInResume);
  const lines = [
    "CAREER TASK LOG",
    `Generated ${new Date().toLocaleDateString("en-IN")}`,
    "",
  ];

  for (const item of included) {
    lines.push(`- ${item.task}`);
    lines.push(`  Date: ${formatDate(item.date)}`);
    if (item.project) lines.push(`  Project: ${item.project}`);
    if (item.technologies.length) {
      lines.push(`  Technologies: ${item.technologies.join(", ")}`);
    }
    if (item.impact) lines.push(`  Impact: ${item.impact}`);
    lines.push("");
  }

  return lines.join("\n").trimEnd() + "\n";
}

export default function Home() {
  const [tasks, setTasks] = useState<CareerTask[]>([]);
  const [draft, setDraft] = useState<TaskDraft>(emptyDraft);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [notice, setNotice] = useState("");
  const [confirmClear, setConfirmClear] = useState(false);
  const taskInputRef = useRef<HTMLTextAreaElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
          const parsed: unknown = JSON.parse(stored);
          if (Array.isArray(parsed)) setTasks(parsed.filter(isCareerTask));
        }
      } catch {
        setNotice(
          "Your saved tasks could not be read. Import a backup to restore them.",
        );
      } finally {
        setLoaded(true);
      }
    });

    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => undefined);
    }

    return () => window.cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    if (!loaded) return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
  }, [loaded, tasks]);

  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(() => setNotice(""), 3200);
    return () => window.clearTimeout(timeout);
  }, [notice]);

  const profile = useMemo(() => {
    const included = tasks.filter((task) => task.includeInResume);
    const skills = Array.from(
      new Set(included.flatMap((task) => task.technologies)),
    ).sort((a, b) => a.localeCompare(b));
    const projects = new Set(
      included.map((task) => task.project.trim()).filter(Boolean),
    );
    const impacts = included.filter((task) => task.impact.trim()).length;
    const score = Math.min(
      100,
      Math.round(
        Math.min(included.length / 5, 1) * 35 +
          Math.min(skills.length / 5, 1) * 25 +
          Math.min(projects.size / 3, 1) * 20 +
          Math.min(impacts / 3, 1) * 20,
      ),
    );

    return { included, skills, projects: projects.size, impacts, score };
  }, [tasks]);

  const visibleTasks = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return tasks;
    return tasks.filter((item) =>
      [
        item.task,
        item.project,
        item.impact,
        item.technologies.join(" "),
      ]
        .join(" ")
        .toLowerCase()
        .includes(query),
    );
  }, [search, tasks]);

  const recentTasks = tasks.slice(0, 3);

  function addTechnologies(raw: string) {
    const additions = raw
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    if (!additions.length) return;

    setDraft((current) => ({
      ...current,
      technologyInput: "",
      technologies: Array.from(
        new Set([...current.technologies, ...additions]),
      ),
    }));
  }

  function handleTechnologyKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      addTechnologies(draft.technologyInput);
    } else if (
      event.key === "Backspace" &&
      !draft.technologyInput &&
      draft.technologies.length
    ) {
      setDraft((current) => ({
        ...current,
        technologies: current.technologies.slice(0, -1),
      }));
    }
  }

  function resetForm() {
    setDraft(emptyDraft());
    setEditingId(null);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const description = draft.task.trim();
    if (!description) {
      taskInputRef.current?.focus();
      setNotice("Describe the work you completed before saving.");
      return;
    }

    const remainingTech = draft.technologyInput.trim();
    const technologies = Array.from(
      new Set([
        ...draft.technologies,
        ...remainingTech
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
      ]),
    );

    if (editingId) {
      setTasks((current) =>
        current.map((item) =>
          item.id === editingId
            ? {
                ...item,
                date: draft.date,
                task: description,
                project: draft.project.trim(),
                technologies,
                impact: draft.impact.trim(),
                includeInResume: draft.includeInResume,
              }
            : item,
        ),
      );
      setNotice("Task updated.");
    } else {
      const item: CareerTask = {
        id: createId(),
        date: draft.date,
        task: description,
        project: draft.project.trim(),
        technologies,
        impact: draft.impact.trim(),
        includeInResume: draft.includeInResume,
        createdAt: new Date().toISOString(),
      };
      setTasks((current) => [item, ...current]);
      setNotice("Task saved on this device.");
    }

    resetForm();
  }

  function editTask(item: CareerTask) {
    setEditingId(item.id);
    setDraft({
      date: item.date,
      task: item.task,
      project: item.project,
      technologyInput: "",
      technologies: item.technologies,
      impact: item.impact,
      includeInResume: item.includeInResume,
    });
    window.scrollTo({ top: 110, behavior: "smooth" });
    window.setTimeout(() => taskInputRef.current?.focus(), 250);
  }

  function removeTask(id: string) {
    setTasks((current) => current.filter((item) => item.id !== id));
    if (editingId === id) resetForm();
    setNotice("Task deleted.");
  }

  async function copyTaskLog() {
    if (!profile.included.length) return;
    try {
      await navigator.clipboard.writeText(buildTaskLog(tasks));
      setNotice("Resume-ready task log copied.");
    } catch {
      downloadTaskLog();
    }
  }

  function downloadTaskLog() {
    if (!profile.included.length) return;
    downloadFile("career-tasklog.txt", buildTaskLog(tasks), "text/plain");
    setNotice("Task log downloaded.");
  }

  function backupTasks() {
    downloadFile(
      `job-agent-backup-${new Date().toISOString().slice(0, 10)}.json`,
      JSON.stringify(tasks, null, 2),
      "application/json",
    );
    setNotice("Private backup downloaded.");
  }

  function importTasks(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed: unknown = JSON.parse(String(reader.result));
        if (!Array.isArray(parsed) || !parsed.every(isCareerTask)) {
          throw new Error("Invalid backup");
        }
        setTasks(parsed);
        setNotice(`${parsed.length} task${parsed.length === 1 ? "" : "s"} restored.`);
      } catch {
        setNotice("That file is not a valid Job Agent backup.");
      }
    };
    reader.readAsText(file);
  }

  function clearAllTasks() {
    setTasks([]);
    resetForm();
    setConfirmClear(false);
    setNotice("All local task data cleared.");
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Job Agent home">
          Job Agent
        </a>
        <div className="topbar-actions">
          <button
            className="text-button desktop-action"
            type="button"
            onClick={copyTaskLog}
            disabled={!profile.included.length}
          >
            Copy task log
          </button>
          <div className="privacy-pill" title="Tasks are stored in this browser">
            <span className="privacy-dot" />
            <span className="shield-mark" aria-hidden="true">◇</span>
            Local only
          </div>
        </div>
      </header>

      <div className="page" id="top">
        <section className="hero" aria-labelledby="page-title">
          <p className="eyebrow">Your private career journal</p>
          <h1 id="page-title">Turn today&apos;s work into tomorrow&apos;s opportunity</h1>
          <p className="hero-copy">
            Capture what you delivered while it is fresh. Job Agent turns your
            verified history into a resume-ready task log—without sending it anywhere.
          </p>
        </section>

        <section className="workspace" aria-label="Career task workspace">
          <div className="primary-column">
            <article className="card form-card">
              <div className="card-heading">
                <div>
                  <p className="section-kicker">{editingId ? "Editing task" : "Quick capture"}</p>
                  <h2>{editingId ? "Update task" : "Add task"}</h2>
                </div>
                {editingId && (
                  <button className="text-button" type="button" onClick={resetForm}>
                    Cancel
                  </button>
                )}
              </div>

              <form onSubmit={handleSubmit}>
                <div className="form-grid">
                  <label className="field field-wide">
                    <span>Task performed <b aria-label="required">*</b></span>
                    <textarea
                      ref={taskInputRef}
                      value={draft.task}
                      maxLength={500}
                      onChange={(event) =>
                        setDraft((current) => ({ ...current, task: event.target.value }))
                      }
                      placeholder="What did you build, improve, investigate or deliver?"
                      rows={4}
                    />
                    <small>{draft.task.length}/500</small>
                  </label>

                  <label className="field">
                    <span>Project</span>
                    <input
                      value={draft.project}
                      maxLength={100}
                      onChange={(event) =>
                        setDraft((current) => ({ ...current, project: event.target.value }))
                      }
                      placeholder="e.g., Payments data platform"
                    />
                  </label>

                  <label className="field">
                    <span>Date</span>
                    <input
                      type="date"
                      value={draft.date}
                      max={new Date().toISOString().slice(0, 10)}
                      onChange={(event) =>
                        setDraft((current) => ({ ...current, date: event.target.value }))
                      }
                    />
                  </label>

                  <div className="field field-wide">
                    <label htmlFor="technologies">Technologies</label>
                    <div className="chip-input-wrap">
                      {draft.technologies.map((technology) => (
                        <button
                          className="technology-chip removable"
                          type="button"
                          key={technology}
                          onClick={() =>
                            setDraft((current) => ({
                              ...current,
                              technologies: current.technologies.filter(
                                (item) => item !== technology,
                              ),
                            }))
                          }
                          aria-label={`Remove ${technology}`}
                        >
                          {technology} <span aria-hidden="true">×</span>
                        </button>
                      ))}
                      <input
                        id="technologies"
                        value={draft.technologyInput}
                        onChange={(event) =>
                          setDraft((current) => ({
                            ...current,
                            technologyInput: event.target.value,
                          }))
                        }
                        onKeyDown={handleTechnologyKeyDown}
                        onBlur={() => addTechnologies(draft.technologyInput)}
                        placeholder={
                          draft.technologies.length
                            ? "Add another"
                            : "Python, AWS Glue, PySpark"
                        }
                      />
                    </div>
                    <small>Press Enter or comma after each technology.</small>
                  </div>

                  <label className="field field-wide">
                    <span>Impact</span>
                    <textarea
                      value={draft.impact}
                      maxLength={300}
                      onChange={(event) =>
                        setDraft((current) => ({ ...current, impact: event.target.value }))
                      }
                      placeholder="What improved? Add numbers where possible."
                      rows={3}
                    />
                    <small>{draft.impact.length}/300</small>
                  </label>
                </div>

                <div className="form-footer">
                  <label className="resume-toggle">
                    <input
                      type="checkbox"
                      checked={draft.includeInResume}
                      onChange={(event) =>
                        setDraft((current) => ({
                          ...current,
                          includeInResume: event.target.checked,
                        }))
                      }
                    />
                    <span>
                      <strong>Include in resume profile</strong>
                      <small>Turn off for confidential or internal-only work.</small>
                    </span>
                  </label>
                  <button className="primary-button" type="submit" disabled={!draft.task.trim()}>
                    {editingId ? "Update task" : "Save task"}
                  </button>
                </div>
              </form>
            </article>

            <article className="card recent-card">
              <div className="card-heading compact">
                <div>
                  <p className="section-kicker">Your momentum</p>
                  <h2>Recent tasks</h2>
                </div>
                <a className="text-link" href="#all-tasks">
                  View all
                </a>
              </div>

              {recentTasks.length ? (
                <div className="recent-list">
                  {recentTasks.map((item) => (
                    <TaskRow
                      key={item.id}
                      item={item}
                      onEdit={editTask}
                      onDelete={removeTask}
                    />
                  ))}
                </div>
              ) : (
                <EmptyState compact />
              )}
            </article>
          </div>

          <aside className="card readiness-card" aria-labelledby="readiness-title">
            <div className="readiness-header">
              <div>
                <p className="section-kicker">Profile health</p>
                <h2 id="readiness-title">Profile readiness</h2>
              </div>
              <div
                className="progress-ring"
                style={{ "--progress": `${profile.score * 3.6}deg` } as React.CSSProperties}
                aria-label={`${profile.score}% complete`}
              >
                <span>{profile.score}%</span>
              </div>
            </div>
            <p className="readiness-copy">
              More specific tasks create stronger matches and more truthful resumes.
            </p>

            <div className="readiness-list">
              <ReadinessItem
                label="Work history"
                detail={`${profile.included.length} resume-ready task${profile.included.length === 1 ? "" : "s"}`}
                complete={profile.included.length >= 5}
                progress={`${Math.min(profile.included.length, 5)} / 5`}
              />
              <ReadinessItem
                label="Skills"
                detail={`${profile.skills.length} verified technolog${profile.skills.length === 1 ? "y" : "ies"}`}
                complete={profile.skills.length >= 5}
                progress={`${Math.min(profile.skills.length, 5)} / 5`}
              />
              <ReadinessItem
                label="Projects"
                detail={`${profile.projects} named project${profile.projects === 1 ? "" : "s"}`}
                complete={profile.projects >= 3}
                progress={`${Math.min(profile.projects, 3)} / 3`}
              />
              <ReadinessItem
                label="Measurable impact"
                detail={`${profile.impacts} task${profile.impacts === 1 ? "" : "s"} with outcomes`}
                complete={profile.impacts >= 3}
                progress={`${Math.min(profile.impacts, 3)} / 3`}
              />
            </div>

            <div className="skills-block">
              <div className="subheading-row">
                <h3>Verified skills</h3>
                <span>{profile.skills.length}</span>
              </div>
              <div className="skill-cloud">
                {profile.skills.length ? (
                  profile.skills.slice(0, 12).map((skill) => (
                    <span className="technology-chip" key={skill}>{skill}</span>
                  ))
                ) : (
                  <p>Add technologies to your tasks to build this list.</p>
                )}
              </div>
            </div>

            <div className="privacy-note">
              <span className="lock-mark" aria-hidden="true">▣</span>
              <div>
                <strong>Your data stays on this device.</strong>
                <p>No account, tracking or cloud upload. Export a backup before changing phones.</p>
              </div>
            </div>

            <div className="aside-actions">
              <button
                className="secondary-button"
                type="button"
                onClick={downloadTaskLog}
                disabled={!profile.included.length}
              >
                Download task log
              </button>
              <button className="text-button" type="button" onClick={backupTasks} disabled={!tasks.length}>
                Download backup
              </button>
            </div>
          </aside>
        </section>

        <section className="all-tasks-section" id="all-tasks" aria-labelledby="all-tasks-title">
          <div className="all-tasks-heading">
            <div>
              <p className="section-kicker">Complete history</p>
              <h2 id="all-tasks-title">All tasks</h2>
              <p>{tasks.length} saved on this device · {profile.included.length} included in exports</p>
            </div>
            <div className="history-actions">
              <label className="search-box">
                <span className="sr-only">Search tasks</span>
                <input
                  type="search"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search tasks or skills"
                />
              </label>
              <button className="secondary-button" type="button" onClick={() => importInputRef.current?.click()}>
                Import backup
              </button>
              <input
                ref={importInputRef}
                className="sr-only"
                type="file"
                accept="application/json,.json"
                onChange={importTasks}
              />
            </div>
          </div>

          {visibleTasks.length ? (
            <div className="task-grid">
              {visibleTasks.map((item) => (
                <TaskCard key={item.id} item={item} onEdit={editTask} onDelete={removeTask} />
              ))}
            </div>
          ) : tasks.length ? (
            <div className="no-results">No tasks match “{search}”.</div>
          ) : (
            <EmptyState />
          )}

          {!!tasks.length && (
            <div className="danger-zone">
              {confirmClear ? (
                <div className="clear-confirmation">
                  <span>This permanently removes every task from this device.</span>
                  <button type="button" className="danger-button" onClick={clearAllTasks}>Clear everything</button>
                  <button type="button" className="text-button" onClick={() => setConfirmClear(false)}>Cancel</button>
                </div>
              ) : (
                <button type="button" className="quiet-danger" onClick={() => setConfirmClear(true)}>
                  Clear local data
                </button>
              )}
            </div>
          )}
        </section>
      </div>

      {notice && <div className="toast" role="status">{notice}</div>}
    </main>
  );
}

function TaskRow({
  item,
  onEdit,
  onDelete,
}: {
  item: CareerTask;
  onEdit: (item: CareerTask) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <div className="task-row">
      <div className="task-icon" aria-hidden="true">↗</div>
      <div className="task-row-copy">
        <strong>{item.task}</strong>
        <span>{item.project || "Independent work"}</span>
      </div>
      <div className="row-skills" aria-label="Technologies">
        {item.technologies.slice(0, 3).map((skill) => (
          <span key={skill}>{skill}</span>
        ))}
      </div>
      <time dateTime={item.date}>{formatDate(item.date)}</time>
      {!item.includeInResume && <span className="private-badge">Private</span>}
      <div className="row-actions">
        <button type="button" onClick={() => onEdit(item)} aria-label={`Edit ${item.task}`}>Edit</button>
        <button type="button" onClick={() => onDelete(item.id)} aria-label={`Delete ${item.task}`}>Delete</button>
      </div>
    </div>
  );
}

function TaskCard({
  item,
  onEdit,
  onDelete,
}: {
  item: CareerTask;
  onEdit: (item: CareerTask) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <article className="task-card">
      <div className="task-card-topline">
        <time dateTime={item.date}>{formatDate(item.date)}</time>
        <span className={item.includeInResume ? "export-badge" : "private-badge"}>
          {item.includeInResume ? "Resume-ready" : "Private"}
        </span>
      </div>
      <h3>{item.task}</h3>
      {item.project && <p className="project-name">{item.project}</p>}
      {item.impact && <p className="impact-copy"><strong>Impact:</strong> {item.impact}</p>}
      <div className="task-card-skills">
        {item.technologies.map((skill) => <span key={skill}>{skill}</span>)}
      </div>
      <div className="task-card-actions">
        <button type="button" onClick={() => onEdit(item)}>Edit</button>
        <button type="button" onClick={() => onDelete(item.id)}>Delete</button>
      </div>
    </article>
  );
}

function ReadinessItem({
  label,
  detail,
  complete,
  progress,
}: {
  label: string;
  detail: string;
  complete: boolean;
  progress: string;
}) {
  return (
    <div className="readiness-item">
      <span className={`readiness-icon ${complete ? "complete" : ""}`} aria-hidden="true">
        {complete ? "✓" : "+"}
      </span>
      <div>
        <strong>{label}</strong>
        <small>{detail}</small>
      </div>
      <span className={`readiness-progress ${complete ? "complete" : ""}`}>{complete ? "Done" : progress}</span>
    </div>
  );
}

function EmptyState({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`empty-state ${compact ? "compact" : ""}`}>
      <span className="empty-mark" aria-hidden="true">＋</span>
      <div>
        <h3>Your task history starts here</h3>
        <p>Add one specific piece of work above. Include the result to make it resume-ready.</p>
      </div>
    </div>
  );
}
