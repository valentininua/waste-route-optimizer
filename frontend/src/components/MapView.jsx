import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { routeStyle } from '../routeStyles';

function toLatLngs(geometry) {
  return (geometry || []).map(([lng, lat]) => [lat, lng]);
}

export function MapView({ points, originalGeometry, optimizedGeometry }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef(null);
  const originalLayerRef = useRef(null);
  const optimizedLayerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current).setView([56.651, 23.721], 12);
    map.createPane('originalRoutePane');
    map.createPane('optimizedRoutePane');
    map.getPane('originalRoutePane').style.zIndex = 430;
    map.getPane('optimizedRoutePane').style.zIndex = 440;

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (markersRef.current) map.removeLayer(markersRef.current);
    const validPoints = (points || []).filter((point) => point.lat && point.lng);
    markersRef.current = L.layerGroup(
      validPoints.map((point) =>
        L.circleMarker([point.lat, point.lng], {
          radius: 5,
          weight: 2,
          fillOpacity: 0.85
        }).bindPopup(`#${point.original_order} → ${point.optimized_order || '-'}<br>${point.address}`)
      )
    ).addTo(map);

    if (validPoints.length) {
      const bounds = L.latLngBounds(validPoints.map((point) => [point.lat, point.lng]));
      map.fitBounds(bounds, { padding: [20, 20] });
    }
  }, [points]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (originalLayerRef.current) map.removeLayer(originalLayerRef.current);
    originalLayerRef.current = null;

    const latLngs = toLatLngs(originalGeometry);
    if (!latLngs.length) return;

    originalLayerRef.current = L.polyline(latLngs, routeStyle('original')).addTo(map);
  }, [originalGeometry]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (optimizedLayerRef.current) map.removeLayer(optimizedLayerRef.current);
    optimizedLayerRef.current = null;

    const latLngs = toLatLngs(optimizedGeometry);
    if (!latLngs.length) return;

    const layer = L.polyline(latLngs, routeStyle('optimized')).addTo(map);
    layer.bringToFront();
    optimizedLayerRef.current = layer;
  }, [optimizedGeometry]);

  return (
    <div>
      <h2>OpenStreetMap View</h2>
      <div className="legend">
        <span className="line original" /> Original route <span className="line optimized" /> Optimized route
      </div>
      <div id="map" ref={containerRef} />
    </div>
  );
}
