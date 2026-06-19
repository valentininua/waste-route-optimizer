export const ROUTE_STYLES = Object.freeze({
  original: Object.freeze({
    pane: 'originalRoutePane',
    className: 'route-line-original',
    color: '#ef4444',
    weight: 3,
    opacity: 0.65,
    dashArray: '8, 8',
    lineCap: 'round',
    lineJoin: 'round'
  }),
  optimized: Object.freeze({
    pane: 'optimizedRoutePane',
    className: 'route-line-optimized',
    color: '#22c55e',
    weight: 5,
    opacity: 0.92,
    dashArray: null,
    lineCap: 'round',
    lineJoin: 'round'
  })
});

export function routeStyle(kind) {
  const style = ROUTE_STYLES[kind];
  if (!style) throw new Error(`Unknown route style kind: ${kind}`);
  return { ...style };
}
