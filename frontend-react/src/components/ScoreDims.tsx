import { DIM_LABELS } from "../lib/types";

export default function ScoreDims({ dims }: { dims?: Record<string, number> | null }) {
  if (!dims || !Object.keys(dims).length) return null;
  return (
    <div className="flex flex-wrap justify-center gap-1.5">
      {Object.entries(DIM_LABELS).map(([k, label]) =>
        dims[k] == null ? null : (
          <span
            key={k}
            className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-700"
          >
            {label} <b className="text-slate-900">{dims[k]}</b>
          </span>
        )
      )}
    </div>
  );
}
