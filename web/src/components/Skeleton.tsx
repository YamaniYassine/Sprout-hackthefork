export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={"animate-pulse bg-slate-200 rounded " + className} />;
}

export function EmptyState({ message = "No evidence found in the corpus." }: { message?: string }) {
  return (
    <div className="text-sm text-slate-400 italic py-6 text-center border border-dashed border-slate-200 rounded-lg">
      {message}
    </div>
  );
}
