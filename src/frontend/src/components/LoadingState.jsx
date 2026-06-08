import { Loader2, AlertCircle, InboxIcon } from 'lucide-react'

export function Spinner({ message = 'Loading data…' }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3 text-brand-muted">
      <Loader2 className="w-8 h-8 animate-spin text-brand-blue" />
      <span className="text-sm font-medium">{message}</span>
    </div>
  )
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3">
      <AlertCircle className="w-8 h-8 text-brand-red" />
      <p className="text-sm font-medium text-gray-700 max-w-md text-center">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-1 px-4 py-1.5 rounded-lg bg-brand-blue text-white text-sm font-semibold
                     hover:bg-brand-navy transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  )
}

export function EmptyState({ message = 'No data matches your filters.' }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3 text-brand-muted">
      <InboxIcon className="w-8 h-8" />
      <span className="text-sm font-medium">{message}</span>
    </div>
  )
}
