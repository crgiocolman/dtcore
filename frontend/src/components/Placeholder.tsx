interface PlaceholderProps {
  title: string
}

export function Placeholder({ title }: PlaceholderProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-bg-surface py-24">
      <p className="text-lg font-medium text-text-secondary">{title}</p>
      <p className="mt-1 text-sm text-text-muted">En construcción</p>
    </div>
  )
}
