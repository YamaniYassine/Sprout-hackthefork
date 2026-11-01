export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={"animate-pulse bg-sprout-paleSage rounded-2xl " + className} />;
}

export function EmptyState({ message = "No evidence found in the corpus." }: { message?: string }) {
  return (
    <div className="text-sm text-sprout-midSage italic py-8 text-center border border-dashed border-sprout-softSage rounded-2xl">
      {message}
    </div>
  );
}
