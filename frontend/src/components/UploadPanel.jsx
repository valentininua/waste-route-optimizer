import { ProgressBar } from './ProgressBar';

export function UploadPanel({
  routes,
  selectedRouteId,
  statusText,
  isBusy,
  progressPercent,
  progressStage,
  onUpload,
  onSelectRoute,
  onLoadRoute,
  onOptimizeRoute,
  onLoadRecentRoutes,
  rawApiResponse
}) {
  return (
    <section className="panel">
      <h2>1. Upload Excel</h2>
      <form onSubmit={onUpload}>
        <input name="file" type="file" accept=".xlsx,.xls" required disabled={isBusy} />
        <button type="submit" disabled={isBusy}>Upload & Parse Routes</button>
      </form>
      <div className="actions">
        <label>
          Route:{' '}
          <select value={selectedRouteId || ''} onChange={(event) => onSelectRoute(event.target.value)} disabled={!routes.length || isBusy}>
            {!routes.length && <option value="">Upload a file first</option>}
            {routes.map((route) => (
              <option key={route.id} value={route.id}>
                {route.route_date || '-'} | {route.route_code || 'Route'} | {route.points_count} points | {route.total_containers} containers | {route.status}
              </option>
            ))}
          </select>
        </label>
        <button type="button" onClick={onLoadRoute} disabled={!selectedRouteId || isBusy}>2. Load Selected Route</button>
        <button type="button" onClick={onOptimizeRoute} disabled={!selectedRouteId || isBusy}>3. Optimize Selected Route</button>
        <button type="button" onClick={onLoadRecentRoutes} disabled={isBusy}>Load Recent Routes</button>
      </div>
      <ProgressBar isBusy={isBusy} progressPercent={progressPercent} stage={progressStage} />
      <pre id="status">{statusText}</pre>

      {rawApiResponse && (
        <details className="api-response-accordion">
          <summary>View raw API response</summary>
          <pre className="command-line">{JSON.stringify(rawApiResponse, null, 2)}</pre>
        </details>
      )}
    </section>
  );
}
