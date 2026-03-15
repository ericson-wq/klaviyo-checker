"""
API Documentation — Vercel Serverless Function

GET / — Returns HTML documentation for the E-commerce Technology Detection API.
"""

import json
from http.server import BaseHTTPRequestHandler


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>E-commerce Technology Detection API</title>
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
  .try-it { background: #fff; border: 1px solid #dee2e6; border-radius: 8px; padding: 1.25rem; margin: 0.75rem 0; }
  .try-it form { display: flex; gap: 0.5rem; }
  .try-it input[type="text"] { flex: 1; padding: 0.5rem 0.75rem; border: 1px solid #ced4da; border-radius: 6px; font-size: 0.95rem; font-family: monospace; outline: none; transition: border-color 0.15s; }
  .try-it input[type="text"]:focus { border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,0.15); }
  .try-it button { padding: 0.5rem 1.25rem; background: #6366f1; color: #fff; border: none; border-radius: 6px; font-size: 0.9rem; font-weight: 600; cursor: pointer; transition: background 0.15s; white-space: nowrap; }
  .try-it button:hover { background: #4f46e5; }
  .try-it button:disabled { background: #a5b4fc; cursor: not-allowed; }
  .result-box { margin-top: 0.75rem; display: none; }
  .result-box.visible { display: block; }
  .result-badge { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.4rem 0.75rem; border-radius: 6px; font-weight: 600; font-size: 0.95rem; margin-bottom: 0.5rem; }
  .result-badge.yes { background: #d3f9d8; color: #087f23; }
  .result-badge.no { background: #ffe0e0; color: #c62828; }
  .result-badge.err { background: #fff3cd; color: #856404; }
  .result-json { background: #1a1a2e; color: #e9ecef; padding: 0.75rem 1rem; border-radius: 6px; font-size: 0.85rem; font-family: monospace; white-space: pre; overflow-x: auto; margin: 0; }
  .result-meta { font-size: 0.8rem; color: #6c757d; margin-top: 0.4rem; }
  .result-signals { margin-top: 0.5rem; display: none; }
  .result-signals.visible { display: block; }
  .result-signals h4 { font-size: 0.85rem; color: #495057; margin-bottom: 0.35rem; }
  .signal-item { display: flex; gap: 0.5rem; align-items: baseline; padding: 0.35rem 0; border-bottom: 1px solid #f1f3f5; font-size: 0.85rem; }
  .signal-item:last-child { border-bottom: none; }
  .signal-type { background: #e8e5ff; color: #4f46e5; padding: 0.1em 0.4em; border-radius: 4px; font-family: monospace; font-size: 0.8rem; white-space: nowrap; }
  .signal-detail { color: #495057; font-family: monospace; font-size: 0.8rem; word-break: break-all; }
  .spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid #fff; border-top-color: transparent; border-radius: 50%; animation: spin 0.6s linear infinite; vertical-align: middle; margin-right: 0.3rem; }
  @keyframes spin { to { transform: rotate(360deg); } }
  footer { margin-top: 3rem; color: #6c757d; font-size: 0.85rem; text-align: center; }
</style>
</head>
<body>
<div class="container">

<h1>E-commerce Technology Detection API</h1>
<p class="subtitle">Check if a website uses Klaviyo, Littledata, or Elevar.</p>

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
<p>All responses return JSON with detection results for Klaviyo, Littledata, and Elevar.</p>

<h3><span class="tag tag-green">200</span> Success</h3>
<pre><code>{
  "domain": "example-store.com",
  "uses_klaviyo": true,
  "signals_matched": [
    {"type": "klaviyo_cdn_script", "detail": "https://static.klaviyo.com/onsite/js/klaviyo.js?company_id=XYZ"}
  ],
  "uses_littledata": false,
  "littledata_signals": [],
  "uses_elevar": true,
  "elevar_signals": [
    {"type": "elevar_datalayer", "detail": "window.ElevarDataLayer reference found"}
  ]
}</code></pre>

<h3><span class="tag tag-green">200</span> Nothing detected</h3>
<pre><code>{
  "domain": "google.com",
  "uses_klaviyo": false,
  "signals_matched": [],
  "uses_littledata": false,
  "littledata_signals": [],
  "uses_elevar": false,
  "elevar_signals": []
}</code></pre>

<h3><span class="tag tag-red">400</span> Bad Request</h3>
<pre><code>{
  "domain": null,
  "uses_klaviyo": false,
  "uses_littledata": false,
  "uses_elevar": false,
  "error": "Domain parameter is required"
}</code></pre>

<h3><span class="tag tag-orange">502 / 504</span> Upstream Error / Timeout</h3>
<pre><code>{
  "domain": "unreachable.example",
  "uses_klaviyo": false,
  "uses_littledata": false,
  "uses_elevar": false,
  "error": "Could not fetch website"
}</code></pre>

<h2>How Detection Works</h2>
<p>The API performs a single HTTP GET request to <code>https://{domain}/</code> and parses the returned HTML. It scans for signals from three technologies. If any signal is found for a technology, the corresponding <code>uses_*</code> field is <code>true</code>.</p>

<h3>Klaviyo Signals (5)</h3>
<table>
  <tr><th>Signal</th><th><code>type</code> value</th><th>What it looks for</th></tr>
  <tr><td>CDN script</td><td><code>klaviyo_cdn_script</code></td><td><code>&lt;script src&gt;</code> containing <code>static.klaviyo.com</code></td></tr>
  <tr><td>Other script</td><td><code>klaviyo_script</code></td><td><code>&lt;script src&gt;</code> containing <code>klaviyo</code> (non-CDN)</td></tr>
  <tr><td><code>_learnq</code> variable</td><td><code>learnq_variable</code></td><td><code>_learnq</code> in inline scripts</td></tr>
  <tr><td>API endpoint</td><td><code>klaviyo_api_endpoint</code></td><td><code>a.klaviyo.com</code> in inline scripts</td></tr>
  <tr><td>Form class</td><td><code>klaviyo_form_class</code></td><td><code>.klaviyo-form</code> class in DOM</td></tr>
</table>

<h3>Littledata Signals (4)</h3>
<table>
  <tr><th>Signal</th><th><code>type</code> value</th><th>What it looks for</th></tr>
  <tr><td>LittledataLayer variable</td><td><code>littledata_layer</code></td><td><code>window.LittledataLayer</code> or <code>LittledataLayer</code> in inline scripts</td></tr>
  <tr><td>Littledata script</td><td><code>littledata_script</code></td><td><code>&lt;script src&gt;</code> containing <code>littledata</code></td></tr>
  <tr><td>Domain reference</td><td><code>littledata_domain</code></td><td><code>littledata.io</code> in inline scripts</td></tr>
  <tr><td>App embed</td><td><code>littledata_app_embed</code></td><td>Shopify app embed block containing <code>littledata</code></td></tr>
</table>

<h3>Elevar Signals (4)</h3>
<table>
  <tr><th>Signal</th><th><code>type</code> value</th><th>What it looks for</th></tr>
  <tr><td>ElevarDataLayer variable</td><td><code>elevar_datalayer</code></td><td><code>window.ElevarDataLayer</code> in inline scripts</td></tr>
  <tr><td>ElevarGtmSuite variable</td><td><code>elevar_gtm_suite</code></td><td><code>window.ElevarGtmSuite</code> in inline scripts</td></tr>
  <tr><td>Elevar script</td><td><code>elevar_script</code></td><td><code>&lt;script src&gt;</code> containing <code>elevar</code> or <code>getelevar</code></td></tr>
  <tr><td>Domain reference</td><td><code>elevar_domain</code></td><td><code>getelevar.com</code> in scripts</td></tr>
</table>

<h3>Limitations</h3>
<ul class="signals">
  <li>Only the initial HTML is analyzed &mdash; scripts loaded dynamically via tag managers (e.g. Google Tag Manager) at runtime won't be detected.</li>
  <li>Only the homepage (<code>/</code>) is checked. A site that loads Klaviyo only on specific pages (e.g. <code>/cart</code>) may be missed.</li>
  <li>Password-protected or geo-blocked sites may return non-HTML responses, resulting in <code>false</code>.</li>
</ul>

<h2>Clay Integration</h2>
<p>To use this API as a Clay HTTP API action:</p>
<ol style="margin: 0.5rem 0; padding-left: 1.25rem;">
  <li>Add an <strong>HTTP API</strong> enrichment column</li>
  <li>Set method to <strong>GET</strong></li>
  <li>Set the URL to: <code>https://klaviyo-detect.vercel.app/api/detect?domain={{domain_column}}</code></li>
  <li>Map <code>uses_klaviyo</code>, <code>uses_littledata</code>, and <code>uses_elevar</code> to your output columns</li>
</ol>

<h2>Try It</h2>
<div class="try-it">
  <form id="tryForm" autocomplete="off">
    <input type="text" id="domainInput" placeholder="e.g. colourpop.com" spellcheck="false">
    <button type="submit" id="tryBtn">Check</button>
  </form>
  <div class="result-box" id="resultBox">
    <div id="resultBadge" class="result-badge"></div>
    <div class="result-signals" id="resultSignals">
      <h4>Signals detected:</h4>
      <div id="signalsList"></div>
    </div>
    <pre class="result-json" id="resultJson"></pre>
    <div class="result-meta" id="resultMeta"></div>
  </div>
</div>

<script>
(function() {
  const form = document.getElementById('tryForm');
  const input = document.getElementById('domainInput');
  const btn = document.getElementById('tryBtn');
  const box = document.getElementById('resultBox');
  const badge = document.getElementById('resultBadge');
  const signalsBox = document.getElementById('resultSignals');
  const signalsList = document.getElementById('signalsList');
  const jsonEl = document.getElementById('resultJson');
  const meta = document.getElementById('resultMeta');

  form.addEventListener('submit', async function(e) {
    e.preventDefault();
    const domain = input.value.trim();
    if (!domain) { input.focus(); return; }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>Checking...';
    box.className = 'result-box visible';
    badge.textContent = '';
    badge.className = 'result-badge';
    signalsBox.className = 'result-signals';
    signalsList.innerHTML = '';
    jsonEl.textContent = '';
    meta.textContent = '';

    const start = performance.now();
    try {
      const resp = await fetch('/api/detect?domain=' + encodeURIComponent(domain));
      const elapsed = ((performance.now() - start) / 1000).toFixed(2);
      const data = await resp.json();

      jsonEl.textContent = JSON.stringify(data, null, 2);
      meta.textContent = resp.status + ' \u2014 ' + elapsed + 's';

      if (data.error) {
        badge.textContent = 'Error: ' + data.error;
        badge.className = 'result-badge err';
      } else {
        var detected = [];
        if (data.uses_klaviyo) detected.push('Klaviyo');
        if (data.uses_littledata) detected.push('Littledata');
        if (data.uses_elevar) detected.push('Elevar');
        if (detected.length > 0) {
          badge.textContent = 'Detected: ' + detected.join(', ');
          badge.className = 'result-badge yes';
        } else {
          badge.textContent = 'No technologies detected';
          badge.className = 'result-badge no';
        }
      }

      // Render all matched signals
      var allSignals = [].concat(
        data.signals_matched || [],
        data.littledata_signals || [],
        data.elevar_signals || []
      );
      if (allSignals.length > 0) {
        signalsBox.className = 'result-signals visible';
        allSignals.forEach(function(s) {
          var row = document.createElement('div');
          row.className = 'signal-item';
          row.innerHTML = '<span class="signal-type">' + escHtml(s.type) + '</span>'
            + '<span class="signal-detail">' + escHtml(s.detail) + '</span>';
          signalsList.appendChild(row);
        });
      }
    } catch (err) {
      badge.textContent = 'Request failed';
      badge.className = 'result-badge err';
      jsonEl.textContent = err.message;
      meta.textContent = '';
    }
    btn.disabled = false;
    btn.textContent = 'Check';
  });

  function escHtml(str) {
    var d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }
})();
</script>

<h2>Examples</h2>
<pre><code># Check a known Klaviyo user
curl "/api/detect?domain=colourpop.com"

# Check a non-Klaviyo site
curl "/api/detect?domain=google.com"

# Handles messy input gracefully
curl "/api/detect?domain=https://www.example.com/page?q=1"</code></pre>

<footer>E-commerce Technology Detection API &middot; Deployed on Vercel</footer>

</div>
</body>
</html>"""


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode())
