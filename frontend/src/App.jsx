import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getOptimizationRun, getRoute, getRouteGeometry, listRoutes, startOptimization, uploadExcel } from './api';
import { CollectionPointsTable } from './components/CollectionPointsTable';
import { Header } from './components/Header';
import { MapView } from './components/MapView';
import { Metrics } from './components/Metrics';
import { UploadPanel } from './components/UploadPanel';
import { renderRouteListSummary, renderRouteSummary, renderRunSummary, renderUploadSummary } from './format';
import './styles.css';

const POLLING_INTERVAL_MS = 2500;

export default function App() {
  const [routes, setRoutes] = useState([]);
  const [selectedRouteId, setSelectedRouteId] = useState('');
  const [currentRoute, setCurrentRoute] = useState(null);
  const [statusText, setStatusText] = useState('Ready.');
  const [rawApiResponse, setRawApiResponse] = useState(null);
  const [isBusy, setIsBusy] = useState(false);
  const [progressPercent, setProgressPercent] = useState(null);
  const [progressStage, setProgressStage] = useState('Idle');
  const [originalGeometry, setOriginalGeometry] = useState([]);
  const [optimizedGeometry, setOptimizedGeometry] = useState([]);
  const pollingRef = useRef(null);

  const selectedRoute = useMemo(
    () => routes.find((route) => String(route.id) === String(selectedRouteId)),
    [routes, selectedRouteId]
  );

  const stopPolling = useCallback(() => {
    if (pollingRef.current) window.clearInterval(pollingRef.current);
    pollingRef.current = null;
  }, []);

  const loadGeometries = useCallback(async (route) => {
    if (!route || route.status !== 'optimized') {
      setOriginalGeometry([]);
      setOptimizedGeometry([]);
      return;
    }

    const [original, optimized] = await Promise.all([
      getRouteGeometry(route.id, 'original'),
      getRouteGeometry(route.id, 'optimized')
    ]);
    setOriginalGeometry(original.geometry || []);
    setOptimizedGeometry(optimized.geometry || []);
  }, []);

  const refreshRoute = useCallback(async (routeId) => {
    const route = await getRoute(routeId);
    setRawApiResponse(route);
    setCurrentRoute(route);
    setStatusText(renderRouteSummary(route));
    await loadGeometries(route);
    return route;
  }, [loadGeometries]);

  const handleUpload = useCallback(async (event) => {
    event.preventDefault();
    const file = event.currentTarget.elements.file.files[0];
    if (!file) return;

    stopPolling();
    setIsBusy(true);
    setProgressPercent(null);
    setProgressStage('Uploading and parsing');
    setStatusText('Uploading and parsing Excel into separate route blocks...');
    setCurrentRoute(null);
    setOriginalGeometry([]);
    setOptimizedGeometry([]);

    try {
      const data = await uploadExcel(file);
      setRawApiResponse(data);
      const parsedRoutes = data.routes || [];
      setRoutes(parsedRoutes);
      setSelectedRouteId(parsedRoutes[0]?.id ? String(parsedRoutes[0].id) : '');
      setStatusText(renderUploadSummary(data));
      setProgressPercent(100);
      setProgressStage('Upload completed');
    } catch (error) {
      setStatusText(error.message);
      setProgressStage('Failed');
    } finally {
      setIsBusy(false);
    }
  }, [stopPolling]);

  const handleLoadRecentRoutes = useCallback(async () => {
    stopPolling();
    setIsBusy(true);
    setProgressPercent(null);
    setProgressStage('Loading routes');
    setStatusText('Loading recent routes...');
    try {
      const recentRoutes = await listRoutes(100);
      setRawApiResponse(recentRoutes);
      setRoutes(recentRoutes || []);
      setSelectedRouteId(recentRoutes?.[0]?.id ? String(recentRoutes[0].id) : '');
      setStatusText(renderRouteListSummary(recentRoutes || []));
      setProgressPercent(100);
      setProgressStage('Routes loaded');
    } catch (error) {
      setStatusText(error.message);
      setProgressStage('Failed');
    } finally {
      setIsBusy(false);
    }
  }, [stopPolling]);

  const handleLoadRoute = useCallback(async () => {
    if (!selectedRouteId) return;
    stopPolling();
    setIsBusy(true);
    setProgressPercent(null);
    setProgressStage('Loading selected route');
    setStatusText('Loading selected route...');
    try {
      await refreshRoute(selectedRouteId);
      setProgressPercent(100);
      setProgressStage('Route loaded');
    } catch (error) {
      setStatusText(error.message);
      setProgressStage('Failed');
    } finally {
      setIsBusy(false);
    }
  }, [refreshRoute, selectedRouteId, stopPolling]);

  const pollRun = useCallback(async (runId) => {
    const run = await getOptimizationRun(runId);
    setRawApiResponse(run);
    setStatusText(renderRunSummary(run));
    setProgressPercent(run.progress_percent ?? 0);
    setProgressStage(run.stage || run.status);
    if (run.route) setCurrentRoute(run.route);

    if (run.status === 'completed') {
      stopPolling();
      await refreshRoute(run.route_job_id);
      setIsBusy(false);
    }

    if (run.status === 'failed') {
      stopPolling();
      await refreshRoute(run.route_job_id);
      setIsBusy(false);
    }
  }, [refreshRoute, stopPolling]);

  const handleOptimizeRoute = useCallback(async () => {
    const routeId = selectedRouteId || selectedRoute?.id;
    if (!routeId) return;

    stopPolling();
    setIsBusy(true);
    setProgressPercent(0);
    setProgressStage('Starting optimization');
    setStatusText('Starting background optimization run. Status is polled through REST API.');

    try {
      const run = await startOptimization(routeId);
      setRawApiResponse(run);
      setStatusText(renderRunSummary(run));
      setProgressPercent(run.progress_percent ?? 0);
      setProgressStage(run.stage || run.status);
      pollingRef.current = window.setInterval(() => {
        pollRun(run.id).catch((error) => {
          stopPolling();
          setIsBusy(false);
          setStatusText(error.message);
        });
      }, POLLING_INTERVAL_MS);
      await pollRun(run.id);
    } catch (error) {
      setStatusText(error.message);
      setProgressStage('Failed');
      setIsBusy(false);
    }
  }, [pollRun, selectedRoute, selectedRouteId, stopPolling]);

  useEffect(() => stopPolling, [stopPolling]);

  return (
    <>
      <Header />
      <main>
        <UploadPanel
          routes={routes}
          selectedRouteId={selectedRouteId}
          statusText={statusText}
          rawApiResponse={rawApiResponse}
          isBusy={isBusy}
          progressPercent={progressPercent}
          progressStage={progressStage}
          onUpload={handleUpload}
          onSelectRoute={setSelectedRouteId}
          onLoadRoute={handleLoadRoute}
          onOptimizeRoute={handleOptimizeRoute}
          onLoadRecentRoutes={handleLoadRecentRoutes}
        />

        <Metrics route={currentRoute} />

        <section className="map-grid">
          <MapView
            points={currentRoute?.points || []}
            originalGeometry={originalGeometry}
            optimizedGeometry={optimizedGeometry}
          />
          <CollectionPointsTable points={currentRoute?.points || []} />
        </section>
      </main>
    </>
  );
}
