export function ProgressBar({ isBusy, progressPercent, stage }) {
  const hasProgress = Number.isFinite(progressPercent);
  const safeProgress = hasProgress ? Math.min(100, Math.max(0, progressPercent)) : 0;
  const label = hasProgress ? `${safeProgress}%` : isBusy ? 'working…' : 'idle';

  return (
    <div className="progress-block" aria-live="polite">
      <div className="progress-meta">
        <span>Progress</span>
        <strong>{stage || label}</strong>
      </div>
      <div
        className={`progress-track ${isBusy && !hasProgress ? 'progress-track-indeterminate' : ''}`}
        role="progressbar"
        aria-valuemin="0"
        aria-valuemax="100"
        aria-valuenow={hasProgress ? safeProgress : undefined}
      >
        <div className="progress-fill" style={{ width: hasProgress ? `${safeProgress}%` : undefined }} />
      </div>
    </div>
  );
}
