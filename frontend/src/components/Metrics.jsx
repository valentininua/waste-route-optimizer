import { formatNumber } from '../format';

function Metric({ label, value }) {
  return (
    <div className="metric">
      <b>{value}</b>
      <span>{label}</span>
    </div>
  );
}

export function Metrics({ route }) {
  const metrics = route?.metrics || {};
  return (
    <section className="metrics">
      <Metric label="Status" value={route?.status || '—'} />
      <Metric label="Points" value={formatNumber(route?.points_count || route?.points?.length)} />
      <Metric label="Original km" value={formatNumber(metrics.original_distance_km)} />
      <Metric label="Optimized km" value={formatNumber(metrics.optimized_distance_km)} />
      <Metric label="Saved km" value={formatNumber(metrics.saved_distance_km)} />
      <Metric label="Saved %" value={formatNumber(metrics.saved_percent)} />
      <Metric label="Original min" value={formatNumber(metrics.original_duration_min)} />
      <Metric label="Optimized min" value={formatNumber(metrics.optimized_duration_min)} />
      {route?.metrics_source && <Metric label="Metrics source" value={route.metrics_source} />}
    </section>
  );
}
