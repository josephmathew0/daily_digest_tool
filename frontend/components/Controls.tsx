import type { Project, User } from "@/services/api";

const phases = ["design", "prototype", "EVT", "DVT", "PVT", "production"];

type Props = {
  projects: Project[];
  users: User[];
  projectId: string;
  userId: string;
  phase: string;
  onProject: (value: string) => void;
  onUser: (value: string) => void;
  onPhase: (value: string) => void;
  onSync: () => void;
};

export function Controls({ projects, users, projectId, userId, phase, onProject, onUser, onPhase, onSync }: Props) {
  return (
    <section className="border-b border-line bg-panel">
      <div className="mx-auto grid max-w-7xl gap-3 px-5 py-4 md:grid-cols-[1.2fr_1.3fr_1fr_auto]">
        <label className="text-sm font-medium">
          Project
          <select className="mt-1 w-full rounded border border-line bg-white px-3 py-2" value={projectId} onChange={(event) => onProject(event.target.value)}>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>{project.name}</option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium">
          View Digest As
          <select className="mt-1 w-full rounded border border-line bg-white px-3 py-2" value={userId} onChange={(event) => onUser(event.target.value)}>
            {users.map((user) => (
              <option key={user.id} value={user.id}>{user.name} - {user.role.replaceAll("_", " ")}</option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium">
          Project Phase
          <select className="mt-1 w-full rounded border border-line bg-white px-3 py-2" value={phase} onChange={(event) => onPhase(event.target.value)}>
            {phases.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </label>
        <button className="self-end rounded bg-ink px-4 py-2 text-sm font-semibold text-white" onClick={onSync}>
          Sync Sources
        </button>
      </div>
    </section>
  );
}
