const API_PREFIX = '/api';

async function request(path, options = {}) {
  const response = await fetch(`${API_PREFIX}${path}`, options);
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail || response.statusText || 'Request failed';
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return data;
}

export function uploadExcel(file) {
  const form = new FormData();
  form.append('file', file);
  return request('/files/upload', { method: 'POST', body: form });
}

export function listRoutes(limit = 100) {
  return request(`/routes?limit=${limit}`);
}

export function getRoute(routeId) {
  return request(`/routes/${routeId}`);
}

export function startOptimization(routeId) {
  return request(`/routes/${routeId}/optimization-runs`, { method: 'POST' });
}

export function getOptimizationRun(runId) {
  return request(`/optimization-runs/${runId}`);
}

export function getRouteGeometry(routeId, kind) {
  return request(`/routes/${routeId}/geometry/${kind}`);
}
