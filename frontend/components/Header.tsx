import { Activity } from "lucide-react";

export function Header() {
  return (
    <header className="border-b border-line bg-white">
      <div className="mx-auto flex max-w-7xl items-center gap-3 px-5 py-4">
        <div className="flex h-9 w-9 items-center justify-center rounded bg-signal text-white">
          <Activity size={20} />
        </div>
        <div>
          <h1 className="text-xl font-semibold tracking-normal">EverCurrent Daily Digest</h1>
          <p className="text-sm text-slate-600">Execution intelligence for hardware engineering teams</p>
        </div>
      </div>
    </header>
  );
}
