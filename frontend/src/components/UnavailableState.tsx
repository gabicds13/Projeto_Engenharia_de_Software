// Estado "indisponível no momento" para uma área isolada (degradação graciosa).
export function UnavailableState({ label }: { label: string }) {
  return (
    <div
      role="status"
      className="flex flex-col items-center justify-center gap-1 rounded-lg border border-border bg-surface p-6 text-center"
    >
      <span className="text-md font-medium text-text">{label} indisponível no momento</span>
      <span className="text-xs text-text-muted">
        Tentaremos reconectar automaticamente.
      </span>
    </div>
  );
}
