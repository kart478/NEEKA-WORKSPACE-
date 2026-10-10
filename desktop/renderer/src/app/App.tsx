import { useEffect, useMemo, useState, type FormEvent, type ReactElement } from "react";
import { apiClient, projectsApi, usersApi } from "../services/api/client";
import { knowledgeApi } from "../services/api/knowledge";
import { tasksApi } from "../services/api/tasks";
import type { ConnectionState } from "./connection";
import "./app.css";

type NavView = "overview" | "projects" | "tasks" | "knowledge" | "files" | "settings";

type UserRecord = { id: string; name: string; email: string; role: string; active: boolean };
type ProjectRecord = { id: string; name: string; description: string; owner_id: string; status: string; member_ids: string[]; task_ids: string[]; created_at: string; updated_at: string };
type TaskRecord = { id: string; project_id: string; title: string; description: string; creator_id: string; assigned_to: string | null; status: string; priority: string; dependency_ids: string[]; created_at: string; updated_at: string; started_at: string | null; completed_at: string | null };
type EventRecord = { event_id: string; event_type: string; timestamp: string; actor_id: string; entity_id: string; metadata?: Record<string, unknown> };
type ArtifactRecord = { id: string; name: string; description: string; mime_type: string; created_at: string; updated_at: string; status?: string };
type KnowledgeBundle = { documents?: unknown[]; requirements?: unknown[]; decisions?: unknown[]; notes?: unknown[]; references?: unknown[]; search?: unknown[] };

type TaskInput = { title: string; description: string; projectId: string };

const ACTOR_KEY = "neeka-local-actor-id";
const navItems: Array<{ id: NavView; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "projects", label: "Projects" },
  { id: "tasks", label: "My Tasks" },
  { id: "knowledge", label: "Knowledge" },
  { id: "files", label: "Files" },
  { id: "settings", label: "Settings" },
];

export function App(): ReactElement {
  const [view, setView] = useState<NavView>("overview");
  const [state, setState] = useState<ConnectionState>("STARTING");
  const [message, setMessage] = useState("Connecting to the local engine...");
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [members, setMembers] = useState<UserRecord[]>([]);
  const [knowledge, setKnowledge] = useState<KnowledgeBundle | null>(null);
  const [artifacts, setArtifacts] = useState<ArtifactRecord[]>([]);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [actorId, setActorId] = useState("");
  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [taskInput, setTaskInput] = useState<TaskInput>({ title: "", description: "", projectId: "" });

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) ?? null,
    [projects, selectedProjectId],
  );

  const filteredProjects = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return projects;
    return projects.filter((project) => `${project.name} ${project.description}`.toLowerCase().includes(term));
  }, [projects, search]);

  const filteredTasks = useMemo(() => {
    const term = search.trim().toLowerCase();
    return tasks.filter((task) => {
      if (!term) return true;
      return `${task.title} ${task.description}`.toLowerCase().includes(term);
    });
  }, [tasks, search]);

  const myTasks = useMemo(() => tasks.filter((task) => task.assigned_to === actorId), [actorId, tasks]);

  useEffect(() => {
    let active = true;
    const check = async () => {
      try {
        const result = await apiClient.health();
        if (!active) return;
        const nextState = result.health?.status === "ok" ? "READY" : "DEGRADED";
        setState(nextState);
        setMessage(result.health?.status === "ok" ? "NEEKA Work Engine is running." : result.error || "Engine is responding unexpectedly.");
      } catch (error) {
        if (!active) return;
        setState("ERROR");
        setMessage(error instanceof Error && error.message ? error.message : "The local engine is unavailable.");
      }
    };
    void check();
    const interval = window.setInterval(() => { void check(); }, 5000);
    return () => { active = false; window.clearInterval(interval); };
  }, []);

  const loadUsers = async (): Promise<void> => {
    const list = await usersApi.list<UserRecord[]>();
    setUsers(list);
    if (list.length > 0 && !actorId) {
      const saved = localStorage.getItem(ACTOR_KEY);
      const nextActor = saved ?? list[0].id;
      setActorId(nextActor);
      localStorage.setItem(ACTOR_KEY, nextActor);
    }
  };

  const ensureActor = async (): Promise<void> => {
    const saved = localStorage.getItem(ACTOR_KEY);
    if (saved) {
      setActorId(saved);
      return;
    }
    try {
      const list = await usersApi.list<UserRecord[]>();
      if (list.length > 0) {
        const nextActor = list[0].id;
        setActorId(nextActor);
        localStorage.setItem(ACTOR_KEY, nextActor);
        return;
      }
      const created = await usersApi.create<UserRecord>({
        name: "Local Workspace User",
        email: "local@neeka.local",
        role: "VIEWER",
      });
      setActorId(created.id);
      localStorage.setItem(ACTOR_KEY, created.id);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Unable to initialize the workspace user.");
    }
  };

  const refreshProjectDetails = async (projectId: string): Promise<void> => {
    if (!actorId) return;
    try {
      const [memberList, knowledgeBundle, artifactList] = await Promise.all([
        projectsApi.members<UserRecord[]>(projectId),
        knowledgeApi.project<KnowledgeBundle>(projectId, actorId),
        projectsApi.artifacts<ArtifactRecord[]>(projectId, actorId),
      ]);
      setMembers(memberList);
      setKnowledge(knowledgeBundle ?? null);
      setArtifacts(artifactList ?? []);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Unable to load project details.");
    }
  };

  const refreshWorkspace = async (): Promise<void> => {
    if (!actorId) return;
    setLoading(true);
    setError("");
    try {
      const [projectList, eventList] = await Promise.all([
        projectsApi.list<ProjectRecord[]>(),
        apiClient.request<EventRecord[]>({ path: "/api/v1/events" }),
      ]);
      setProjects(projectList);
      setEvents(eventList);
      if (projectList.length && !selectedProjectId) {
        setSelectedProjectId(projectList[0].id);
      }
      const projectTasks = await Promise.all(
        projectList.map(async (project) => {
          try {
            return await tasksApi.listByProject<TaskRecord[]>(project.id);
          } catch {
            return [] as TaskRecord[];
          }
        }),
      );
      setTasks(projectTasks.flat());
      if (selectedProjectId) {
        await refreshProjectDetails(selectedProjectId);
      }
      if (taskInput.projectId === "" && projectList[0]) {
        setTaskInput((current) => ({ ...current, projectId: projectList[0].id }));
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : "Unable to refresh the workspace.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void ensureActor();
  }, []);

  useEffect(() => {
    if (!actorId) return;
    void loadUsers();
    void refreshWorkspace();
  }, [actorId]);

  useEffect(() => {
    if (!selectedProjectId || !actorId) return;
    void refreshProjectDetails(selectedProjectId);
  }, [selectedProjectId, actorId]);

  const handleCreateProject = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    if (!actorId) return;
    try {
      const created = await projectsApi.create<ProjectRecord>({
        name: projectName.trim(),
        description: projectDescription.trim(),
        owner_id: actorId,
      });
      setSelectedProjectId(created.id);
      setView("projects");
      setProjectName("");
      setProjectDescription("");
      await refreshWorkspace();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Project creation failed.");
    }
  };

  const handleCreateTask = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    if (!actorId) return;
    try {
      await tasksApi.create(taskInput.projectId, {
        title: taskInput.title.trim(),
        description: taskInput.description.trim(),
        creator_id: actorId,
        priority: "MEDIUM",
      });
      setTaskInput((current) => ({ ...current, title: "", description: "" }));
      await refreshWorkspace();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Task creation failed.");
    }
  };

  const transitionTask = async (taskId: string, action: "start" | "complete" | "block" | "cancel") => {
    if (!actorId) return;
    try {
      if (action === "start") await tasksApi.start(taskId, actorId);
      if (action === "complete") await tasksApi.complete(taskId, actorId);
      if (action === "block") await tasksApi.block(taskId, actorId);
      if (action === "cancel") await tasksApi.cancel(taskId, actorId);
      await refreshWorkspace();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Unable to update task status.");
    }
  };

  const openProject = (projectId: string): void => {
    setSelectedProjectId(projectId);
    setView("projects");
  };

  const taskStats = {
    total: tasks.length,
    todo: tasks.filter((task) => task.status === "TODO").length,
    inProgress: tasks.filter((task) => task.status === "IN_PROGRESS").length,
    blocked: tasks.filter((task) => task.status === "BLOCKED").length,
    completed: tasks.filter((task) => task.status === "COMPLETED").length,
  };

  const renderOverview = (): ReactElement => (
    <section className="page-grid">
      <div className="stats-grid">
        <div className="stat-card"><span className="stat-label">Active projects</span><strong>{projects.length}</strong><small>{projects.filter((project) => project.status !== "ARCHIVED").length} live</small></div>
        <div className="stat-card"><span className="stat-label">Assigned work</span><strong>{myTasks.length}</strong><small>{myTasks.filter((task) => task.status === "IN_PROGRESS").length} active</small></div>
        <div className="stat-card"><span className="stat-label">Tasks in flight</span><strong>{taskStats.inProgress}</strong><small>{taskStats.todo} queued</small></div>
        <div className="stat-card"><span className="stat-label">Blocked</span><strong>{taskStats.blocked}</strong><small>{taskStats.completed} complete</small></div>
      </div>

      <div className="content-grid">
        <div className="panel">
          <div className="panel-header"><h3>Quick actions</h3></div>
          <form className="stack-form" onSubmit={handleCreateProject}>
            <label>
              <span>Project name</span>
              <input value={projectName} onChange={(event) => setProjectName(event.target.value)} placeholder="Launch campaign" required />
            </label>
            <label>
              <span>Description</span>
              <textarea value={projectDescription} onChange={(event) => setProjectDescription(event.target.value)} placeholder="Define scope and intent" rows={3} />
            </label>
            <button type="submit" className="primary-button">Create project</button>
          </form>
        </div>

        <div className="panel">
          <div className="panel-header"><h3>Create task</h3></div>
          <form className="stack-form" onSubmit={handleCreateTask}>
            <label>
              <span>Project</span>
              <select value={taskInput.projectId} onChange={(event) => setTaskInput((current) => ({ ...current, projectId: event.target.value }))} required>
                <option value="">Select a project</option>
                {projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}
              </select>
            </label>
            <label>
              <span>Task title</span>
              <input value={taskInput.title} onChange={(event) => setTaskInput((current) => ({ ...current, title: event.target.value }))} placeholder="Draft release plan" required />
            </label>
            <label>
              <span>Details</span>
              <textarea value={taskInput.description} onChange={(event) => setTaskInput((current) => ({ ...current, description: event.target.value }))} placeholder="What needs to happen?" rows={3} />
            </label>
            <button type="submit" className="primary-button">Create task</button>
          </form>
        </div>
      </div>

      <div className="panel wide-panel">
        <div className="panel-header"><h3>Projects</h3><button className="text-button" type="button" onClick={() => setView("projects")}>Open all</button></div>
        <div className="list-rows">
          {filteredProjects.slice(0, 5).map((project) => (
            <div className="list-row" key={project.id}>
              <div>
                <div className="row-title">{project.name}</div>
                <div className="row-meta">{project.status} · {project.member_ids.length} members</div>
              </div>
              <button className="secondary-button" type="button" onClick={() => openProject(project.id)}>Open</button>
            </div>
          ))}
        </div>
      </div>

      <div className="panel wide-panel">
        <div className="panel-header"><h3>Outstanding work</h3><button className="text-button" type="button" onClick={() => setView("tasks")}>View all</button></div>
        <div className="list-rows">
          {filteredTasks.filter((task) => task.status !== "COMPLETED").slice(0, 6).map((task) => (
            <div className="list-row" key={task.id}>
              <div>
                <div className="row-title">{task.title}</div>
                <div className="row-meta">{task.status} · {task.priority} · {projects.find((project) => project.id === task.project_id)?.name ?? "Unassigned project"}</div>
              </div>
              <button className="secondary-button" type="button" onClick={() => setView("tasks")}>Review</button>
            </div>
          ))}
        </div>
      </div>

      <div className="panel wide-panel">
        <div className="panel-header"><h3>Recent activity</h3></div>
        <div className="activity-list">
          {events.slice(0, 8).map((event) => (
            <div className="activity-item" key={event.event_id}>
              <span className="event-pill">{event.event_type}</span>
              <div>
                <strong>{event.entity_id}</strong>
                <small>{new Date(event.timestamp).toLocaleString()}</small>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );

  const renderProjects = (): ReactElement => (
    <section className="page-block">
      <div className="section-header">
        <div>
          <p className="eyebrow">Portfolio</p>
          <h2>Projects</h2>
        </div>
      </div>
      <div className="project-grid">
        {filteredProjects.map((project) => {
          const projectTasks = tasks.filter((task) => task.project_id === project.id);
          const progress = projectTasks.length ? Math.round((projectTasks.filter((task) => task.status === "COMPLETED").length / projectTasks.length) * 100) : 0;
          return (
            <article className="card" key={project.id}>
              <div className="card-header">
                <div>
                  <h3>{project.name}</h3>
                  <span className="status-chip">{project.status}</span>
                </div>
                <button className="secondary-button" type="button" onClick={() => openProject(project.id)}>Open</button>
              </div>
              <p>{project.description || "No project summary provided."}</p>
              <div className="mini-metrics">
                <span>{projectTasks.length} tasks</span>
                <span>{project.member_ids.length} members</span>
                <span>{progress}% done</span>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );

  const renderTasks = (): ReactElement => (
    <section className="page-block">
      <div className="section-header">
        <div>
          <p className="eyebrow">Execution</p>
          <h2>My Tasks</h2>
        </div>
      </div>
      <div className="task-list">
        {filteredTasks.map((task) => {
          const project = projects.find((item) => item.id === task.project_id);
          return (
            <div className="task-item" key={task.id}>
              <div className="task-primary">
                <span className={`priority-badge ${task.priority.toLowerCase()}`}>{task.priority}</span>
                <div>
                  <h4>{task.title}</h4>
                  <p>{project?.name ?? "Project"} · {task.status}</p>
                </div>
              </div>
              <div className="task-actions">
                {task.status === "TODO" && <button className="secondary-button" type="button" onClick={() => transitionTask(task.id, "start")}>Start</button>}
                {task.status === "IN_PROGRESS" && <button className="secondary-button" type="button" onClick={() => transitionTask(task.id, "complete")}>Complete</button>}
                {task.status !== "BLOCKED" && <button className="secondary-button" type="button" onClick={() => transitionTask(task.id, "block")}>Block</button>}
                {task.status !== "CANCELLED" && <button className="secondary-button" type="button" onClick={() => transitionTask(task.id, "cancel")}>Cancel</button>}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );

  const renderKnowledge = (): ReactElement => (
    <section className="page-block">
      <div className="section-header">
        <div>
          <p className="eyebrow">Knowledge</p>
          <h2>{selectedProject ? selectedProject.name : "Project knowledge"}</h2>
        </div>
      </div>
      <div className="knowledge-grid">
        <div className="card knowledge-card">
          <h3>Documents</h3>
          <ul>{(knowledge?.documents ?? []).slice(0, 4).map((item: unknown, index: number) => <li key={index}>{String((item as Record<string, unknown>).title ?? "Document")}</li>)}</ul>
        </div>
        <div className="card knowledge-card">
          <h3>Requirements</h3>
          <ul>{(knowledge?.requirements ?? []).slice(0, 4).map((item: unknown, index: number) => <li key={index}>{String((item as Record<string, unknown>).title ?? "Requirement")}</li>)}</ul>
        </div>
        <div className="card knowledge-card">
          <h3>Decisions</h3>
          <ul>{(knowledge?.decisions ?? []).slice(0, 4).map((item: unknown, index: number) => <li key={index}>{String((item as Record<string, unknown>).title ?? "Decision")}</li>)}</ul>
        </div>
        <div className="card knowledge-card">
          <h3>Notes</h3>
          <ul>{(knowledge?.notes ?? []).slice(0, 4).map((item: unknown, index: number) => <li key={index}>{String((item as Record<string, unknown>).title ?? "Note")}</li>)}</ul>
        </div>
      </div>
    </section>
  );

  const renderFiles = (): ReactElement => (
    <section className="page-block">
      <div className="section-header">
        <div>
          <p className="eyebrow">Storage</p>
          <h2>Files</h2>
        </div>
      </div>
      <div className="list-rows">
        {artifacts.length === 0 ? <p className="empty-state">No artifacts are attached to this project yet.</p> : artifacts.map((artifact) => (
          <div className="list-row" key={artifact.id}>
            <div>
              <div className="row-title">{artifact.name}</div>
              <div className="row-meta">{artifact.mime_type} · {new Date(artifact.created_at).toLocaleDateString()}</div>
            </div>
            <span className="status-chip">{artifact.status ?? "READY"}</span>
          </div>
        ))}
      </div>
    </section>
  );

  const renderSettings = (): ReactElement => (
    <section className="page-block">
      <div className="section-header">
        <div>
          <p className="eyebrow">System</p>
          <h2>Settings</h2>
        </div>
      </div>
      <div className="settings-grid">
        <div className="card">
          <h3>Session</h3>
          <ul className="meta-list">
            <li><span>Current user</span><strong>{users.find((user) => user.id === actorId)?.name ?? "Workspace user"}</strong></li>
            <li><span>Connection</span><strong>{state}</strong></li>
            <li><span>Backend</span><strong>{message}</strong></li>
          </ul>
        </div>
        <div className="card">
          <h3>Workspace</h3>
          <ul className="meta-list">
            <li><span>Projects</span><strong>{projects.length}</strong></li>
            <li><span>Tasks</span><strong>{tasks.length}</strong></li>
            <li><span>Members</span><strong>{users.length}</strong></li>
          </ul>
        </div>
      </div>
    </section>
  );

  const selectedProjectName = selectedProject ? selectedProject.name : "Workspace";

  return (
    <main className="workspace-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">N</div>
          <div>
            <div className="brand-name">NEEKA</div>
            <span className="brand-subtitle">Work Engine</span>
          </div>
        </div>
        <nav className="nav-column" aria-label="Primary navigation">
          {navItems.map((item) => (
            <button key={item.id} type="button" className={`nav-button ${view === item.id ? "active" : ""}`} onClick={() => setView(item.id)}>
              {item.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className={`connection-pill status-${state.toLowerCase()}`}>
            <span className="dot" />
            {state}
          </div>
          <span className="version-tag">v0.2.0</span>
        </div>
      </aside>

      <div className="workspace-panel">
        <header className="workspace-header">
          <div>
            <p className="header-label">{selectedProjectName}</p>
            <h1>{view === "overview" ? "Overview" : navItems.find((item) => item.id === view)?.label ?? "Workspace"}</h1>
          </div>
          <div className="header-tools">
            <div className="search-box">
              <span>⌕</span>
              <input type="search" aria-label="Search workspace" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search" />
            </div>
            <div className="profile-pill">
              <span className="profile-avatar">{users.find((user) => user.id === actorId)?.name?.slice(0, 1).toUpperCase() ?? "W"}</span>
              <div>
                <strong>{users.find((user) => user.id === actorId)?.name ?? "Workspace user"}</strong>
                <small>{actorId ? "Local session" : "No user"}</small>
              </div>
            </div>
          </div>
        </header>

        {error ? <div className="banner error-banner">{error}</div> : null}
        {loading ? <div className="banner">Loading workspace…</div> : null}

        {view === "overview" ? renderOverview() : null}
        {view === "projects" ? renderProjects() : null}
        {view === "tasks" ? renderTasks() : null}
        {view === "knowledge" ? renderKnowledge() : null}
        {view === "files" ? renderFiles() : null}
        {view === "settings" ? renderSettings() : null}
      </div>
    </main>
  );
}