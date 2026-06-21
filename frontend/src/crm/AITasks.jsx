import { useState } from "react";

import { getTask } from "./api";

export default function AITasks() {
  const [taskId, setTaskId] = useState("");
  const [task, setTask] = useState(null);

  async function lookup() {
    setTask(await getTask(taskId));
  }

  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-2xl font-semibold">AI Tasks</h2>
        <p className="text-sm text-slate-400">Poll queued AI, sync, scoring, and campaign jobs without blocking the UI.</p>
      </div>
      <div className="flex max-w-xl gap-2">
        <input value={taskId} onChange={(e) => setTaskId(e.target.value)} placeholder="Task ID" className="min-w-0 flex-1 rounded-md border border-white/10 bg-black/20 px-3 py-2 text-sm outline-none focus:border-cyan-400" />
        <button onClick={lookup} className="rounded-md bg-cyan-400 px-3 py-2 text-sm font-medium text-slate-950">Check</button>
      </div>
      {task && <pre className="overflow-auto rounded-lg border border-white/10 bg-black/20 p-4 text-sm text-slate-300">{JSON.stringify(task, null, 2)}</pre>}
    </section>
  );
}
