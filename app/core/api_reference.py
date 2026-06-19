from __future__ import annotations

from html import escape
from typing import Any

HTTP_METHOD_ORDER = ("get", "post", "put", "patch", "delete", "options", "head")


def render_api_reference_html(openapi_schema: dict[str, Any]) -> str:
    """
      Lightweight API reference
    """

    title = escape(openapi_schema.get("info", {}).get("title", "API Reference"))
    version = escape(openapi_schema.get("info", {}).get("version", ""))
    description = escape(openapi_schema.get("info", {}).get("description", ""))
    rows = []

    for path, path_item in sorted(openapi_schema.get("paths", {}).items()):
        if not isinstance(path_item, dict):
            continue
        for method in HTTP_METHOD_ORDER:
            operation = path_item.get(method)
            if not operation:
                continue
            summary = escape(operation.get("summary") or operation.get("operationId") or "")
            tags = ", ".join(operation.get("tags") or [])
            rows.append(
                """
                <tr>
                    <td><span class="method method-{method}">{method_upper}</span></td>
                    <td><code>{path}</code></td>
                    <td>{summary}</td>
                    <td>{tags}</td>
                </tr>
                """.format(
                    method=escape(method),
                    method_upper=escape(method.upper()),
                    path=escape(path),
                    summary=summary,
                    tags=escape(tags),
                )
            )

    operations_html = "\n".join(rows) or "<tr><td colspan='4'>No operations found.</td></tr>"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} · API Reference</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin: 0; background: #f8fafc; color: #0f172a; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }}
    header {{ margin-bottom: 24px; }}
    h1 {{ margin: 0 0 8px; font-size: 32px; }}
    p {{ color: #475569; line-height: 1.6; }}
    .links {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 18px 0 28px; }}
    .links a {{ color: #0f766e; background: #ecfeff; border: 1px solid #99f6e4; border-radius: 10px; padding: 9px 12px; text-decoration: none; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #e2e8f0; border-radius: 14px; overflow: hidden; box-shadow: 0 12px 30px rgba(15, 23, 42, .08); }}
    th, td {{ padding: 13px 14px; text-align: left; border-bottom: 1px solid #e2e8f0; vertical-align: top; }}
    th {{ background: #f1f5f9; color: #334155; font-size: 13px; text-transform: uppercase; letter-spacing: .04em; }}
    tr:last-child td {{ border-bottom: 0; }}
    code {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 7px; padding: 3px 6px; }}
    .method {{ display: inline-block; min-width: 56px; text-align: center; border-radius: 999px; padding: 5px 9px; color: white; font-size: 12px; font-weight: 800; }}
    .method-get {{ background: #2563eb; }}
    .method-post {{ background: #16a34a; }}
    .method-put, .method-patch {{ background: #d97706; }}
    .method-delete {{ background: #dc2626; }}
    .version {{ color: #64748b; font-size: 14px; }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{title}</h1>
      <div class="version">Version {version}</div>
      <p>{description}</p>
      <div class="links">
        <a href="/">Web UI</a>
        <a href="/docs">Swagger UI</a>
        <a href="/openapi.json">OpenAPI JSON</a>
        <a href="/health">Health</a>
      </div>
    </header>
    <table aria-label="API operations">
      <thead>
        <tr><th>Method</th><th>Path</th><th>Summary</th><th>Tags</th></tr>
      </thead>
      <tbody>{operations_html}</tbody>
    </table>
  </main>
</body>
</html>"""
