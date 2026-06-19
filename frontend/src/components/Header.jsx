import { useState } from 'react';

const GITHUB_REPOSITORY_URL = 'https://github.com/valentininua/waste-route-optimizer';

export function Header() {
  const [isHelpOpen, setIsHelpOpen] = useState(false);

  return (
    <header>
      <div className="header-main">
        <div>
          <h1>Waste Route Optimizer</h1>
          <p>Excel import → route selection → geocoding → road-based routing → optimized collection route</p>
        </div>
        <nav className="top-menu" aria-label="Application navigation">
          <a href="/" aria-current="page">Web UI</a>
          <a href="/docs" target="_blank" rel="noreferrer">Swagger UI</a>
          <a href="/redoc" target="_blank" rel="noreferrer">API Reference</a>
          <a href="/openapi.json" target="_blank" rel="noreferrer">OpenAPI JSON</a>
          <a href="/health" target="_blank" rel="noreferrer">Health</a>
          <a href={GITHUB_REPOSITORY_URL} target="_blank" rel="noreferrer">GitHub</a>
          <button className="menu-button" type="button" onClick={() => setIsHelpOpen(true)}>Help</button>
        </nav>
      </div>

      {isHelpOpen && (
        <div className="modal-backdrop" role="presentation" onClick={() => setIsHelpOpen(false)}>
          <div className="help-modal" role="dialog" aria-modal="true" aria-labelledby="help-title" onClick={(event) => event.stopPropagation()}>
            <div className="help-modal-head">
              <h2 id="help-title">How to use this tool</h2>
              <button className="icon-button" type="button" aria-label="Close help" onClick={() => setIsHelpOpen(false)}>×</button>
            </div>
            <ol>
              <li>Upload the Excel file with waste collection routes.</li>
              <li>Select one route from the dropdown list.</li>
              <li>Click <b>Load Selected Route</b> to inspect points and existing metrics.</li>
              <li>Click <b>Optimize Selected Route</b> to start background optimization.</li>
              <li>Wait for the progress bar to reach 100%.</li>
              <li>Compare the red original route with the green optimized route on the map.</li>
            </ol>
            <p className="help-note">
              {/* OSRM/Nominatim services have rate limits */}
            </p>
          </div>
        </div>
      )}
    </header>
  );
}
