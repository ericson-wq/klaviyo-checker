"""
API Documentation — Vercel Serverless Function

GET / — Returns HTML documentation for the Klaviyo Detection API.
"""

import json
from http.server import BaseHTTPRequestHandler


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Klaviyo Detection API</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1a1a2e; background: #f8f9fa; padding: 2rem 1rem; }
  .container { max-width: 720px; margin: 0 auto; }
  h1 { font-size: 1.75rem; margin-bottom: 0.25rem; }
  .subtitle { color: #6c757d; margin-bottom: 2rem; }
  h2 { font-size: 1.2rem; margin: 2rem 0 0.75rem; border-bottom: 1px solid #dee2e6; padding-bottom: 0.25rem; }
  h3 { font-size: 1rem; margin: 1.25rem 0 0.5rem; }
  code { background: #e9ecef; padding: 0.15em 0.4em; border-radius: 4px; font-size: 0.9em; }
  pre { background: #1a1a2e; color: #e9ecef; padding: 1rem; border-radius: 8px; overflow-x: auto; margin: 0.75rem 0; font-size: 0.85rem; line-height: 1.5; }
  pre code { background: none; padding: 0; color: inherit; }
  .endpoint { background: #fff; border: 1px solid #dee2e6; border-radius: 8px; padding: 1rem 1.25rem; margin: 0.75rem 0; }
  .method { display: inline-block; background: #198754; color: #fff; padding: 0.15em 0.5em; border-radius: 4px; font-weight: 600; font-size: 0.85rem; margin-right: 0.5rem; }
  .path { font-family: monospace; font-size: 0.95rem; }
  table { width: 100%; border-collapse: collapse; margin: 0.75rem 0; font-size: 0.9rem; }
  th, td { text-align: left; padding: 0.5rem 0.75rem; border: 1px solid #dee2e6; }
  th { background: #f1f3f5; }
  .tag { display: inline-block; padding: 0.1em 0.4em; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
  .tag-green { background: #d3f9d8; color: #087f23; }
  .tag-red { background: #ffe0e0; color: #c62828; }
  .tag-orange { background: #fff3cd; color: #856404; }
  .signals li { margin: 0.3rem 0; }
  footer { margin-top: 3rem; color: #6c757d; font-size: 0.85rem; text-align: center; }
</style>
</head>
<body>
<div class="container">

<h1>Klaviyo Detection API</h1>
<p class="subtitle">Check if a website uses Klaviyo for email marketing.</p>

<h2>Endpoint</h2>
<div class="endpoint">
  <span class="method">GET</span>
  <span class="path">/api/detect?domain=example.com</span>
</div>

<h2>Parameters</h2>
<table>
  <tr><th>Name</th><th>Type</th><th>Required</th><th>Description</th></tr>
  <tr><td><code>domain</code></td><td>string</td><td>Yes</td><td>Domain to check (e.g. <code>gymshark.com</code>). Protocol, paths, and ports are stripped automatically.</td></tr>
</table>

<h2>Response</h2>
<p>All responses return JSON. The <code>uses_klaviyo</code> field is always present.</p>

<h3><span class="tag tag-green">200</span> Success</h3>
<pre><code>{
  "domain": "gymshark.com",
  "uses_klaviyo": true
}</code></pre>

<h3><span class="tag tag-red">400</span> Bad Request</h3>
<pre><code>{
  "domain": null,
  "uses_klaviyo": false,
  "error": "Domain parameter is required"
}</code></pre>
<pre><code>{
  "domain": "not valid!",
  "uses_klaviyo": false,
  "error": "Invalid domain format"
}</code></pre>

<h3><span class="tag tag-orange">502</span> Upstream Error</h3>
<pre><code>{
  "domain": "unreachable.example",
  "uses_klaviyo": false,
  "error": "Could not fetch website"
}</code></pre>

<h3><span class="tag tag-orange">504</span> Timeout</h3>
<pre><code>{
  "domain": "slow.example",
  "uses_klaviyo": false,
  "error": "Website timed out"
}</code></pre>

<h2>Detection Signals</h2>
<p>The API fetches the homepage HTML and checks for these Klaviyo indicators:</p>
<ul class="signals">
  <li>Script tags loading from <code>static.klaviyo.com</code></li>
  <li>Any script src containing <code>klaviyo</code></li>
  <li><code>_learnq</code> variable in inline scripts (Klaviyo's tracking object)</li>
  <li>References to <code>a.klaviyo.com</code> (Klaviyo API endpoint)</li>
  <li><code>.klaviyo-form</code> CSS class in the DOM</li>
</ul>
<p>If <strong>any</strong> signal is found, <code>uses_klaviyo</code> is <code>true</code>.</p>

<h2>Clay Integration</h2>
<p>To use this API as a Clay HTTP API action:</p>
<ol style="margin: 0.5rem 0; padding-left: 1.25rem;">
  <li>Add an <strong>HTTP API</strong> enrichment column</li>
  <li>Set method to <strong>GET</strong></li>
  <li>Set the URL to: <code>https://&lt;your-vercel-url&gt;/api/detect?domain={{domain_column}}</code></li>
  <li>Map <code>uses_klaviyo</code> from the response to your output column</li>
</ol>

<h2>Examples</h2>
<pre><code># Check a known Klaviyo user
curl "/api/detect?domain=gymshark.com"

# Check a non-Klaviyo site
curl "/api/detect?domain=google.com"

# Handles messy input gracefully
curl "/api/detect?domain=https://www.example.com/page?q=1"</code></pre>

<footer>Klaviyo Detection API &middot; Deployed on Vercel</footer>

</div>
</body>
</html>"""


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode())
