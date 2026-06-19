export function CollectionPointsTable({ points }) {
  return (
    <div>
      <h2>Collection Points</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Old</th>
              <th>New</th>
              <th>Address</th>
              <th>Service</th>
              <th>Freq.</th>
              <th>Vol.</th>
              <th>Cnt.</th>
            </tr>
          </thead>
          <tbody>
            {(points || []).map((point) => (
              <tr key={point.id}>
                <td>{point.original_order ?? ''}</td>
                <td>{point.optimized_order ?? ''}</td>
                <td>{point.address}</td>
                <td>{point.service_day_code || ''}</td>
                <td>{point.frequency_code || ''}</td>
                <td>{point.volume ?? 0}</td>
                <td>{point.containers ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
