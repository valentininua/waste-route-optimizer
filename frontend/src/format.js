export function formatNumber(value) {
  return value === null || value === undefined ? '—' : Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function renderUploadSummary(data) {
  return [
    'Upload completed.',
    `Filename: ${data.filename}`,
    `Routes parsed: ${data.routes_count}`,
    `Routes returned in selector: ${data.returned_routes_count ?? (data.routes || []).length}`,
    `Collection points parsed: ${data.points_count}`,
    `Previous imports for this filename replaced: ${data.replace_existing ? 'yes' : 'no'}`,
    'Next step: select one route and click “Load Selected Route”.'
  ].join('\n');
}

export function renderRouteListSummary(routes) {
  const optimized = routes.filter((route) => route.status === 'optimized').length;
  const parsed = routes.filter((route) => route.status === 'parsed').length;
  const failed = routes.filter((route) => route.status === 'failed').length;
  return [
    `Routes loaded: ${routes.length}`,
    `Optimized: ${optimized}`,
    `Parsed/not optimized: ${parsed}`,
    `Failed: ${failed}`,
    'Select a route from the dropdown to inspect or optimize it.'
  ].join('\n');
}

export function renderRouteSummary(route) {
  const metrics = route.metrics || {};
  return [
    `Route: ${route.route_date || '-'} | ${route.route_code || '-'} | id=${route.id}`,
    `Status: ${route.status}`,
    `Points: ${route.points_count}`,
    `Containers: ${route.total_containers} / declared ${route.declared_total_containers ?? '—'}`,
    `Volume: ${formatNumber(route.total_volume)} / declared ${formatNumber(route.declared_total_volume)}`,
    route.metrics ? `Original: ${formatNumber(metrics.original_distance_km)} km, ${formatNumber(metrics.original_duration_min)} min` : 'Original: not calculated yet',
    route.metrics ? `Optimized: ${formatNumber(metrics.optimized_distance_km)} km, ${formatNumber(metrics.optimized_duration_min)} min` : 'Optimized: not calculated yet',
    route.metrics ? `Saved: ${formatNumber(metrics.saved_distance_km)} km (${formatNumber(metrics.saved_percent)}%)` : 'Saved: not calculated yet',
    route.metrics_source ? `Metrics source: ${route.metrics_source}` : 'Metrics source: not available yet',
    route.error ? `Error: ${route.error}` : null
  ].filter(Boolean).join('\n');
}

export function renderRunSummary(run) {
  return [
    `Optimization run #${run.id}`,
    `Route job id: ${run.route_job_id}`,
    `Status: ${run.status}`,
    `Stage: ${run.stage || '—'}`,
    `Progress: ${run.progress_percent ?? 0}%`,
    run.message ? `Message: ${run.message}` : null,
    run.error ? `Error: ${run.error}` : null
  ].filter(Boolean).join('\n');
}
