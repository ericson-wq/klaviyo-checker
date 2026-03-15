# E-commerce Technology Detection API

Detect whether a website uses **Klaviyo**, **Littledata**, or **Elevar** by scanning its HTML for technology-specific signals.

## API Usage

```
GET /api/detect?domain=example.com
```

### Example Response

```json
{
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
}
```

### Detection Signals

| Technology | Signal | `type` value |
|---|---|---|
| **Klaviyo** | CDN script (`static.klaviyo.com`) | `klaviyo_cdn_script` |
| | Other Klaviyo script | `klaviyo_script` |
| | `_learnq` variable | `learnq_variable` |
| | API endpoint (`a.klaviyo.com`) | `klaviyo_api_endpoint` |
| | `.klaviyo-form` class | `klaviyo_form_class` |
| **Littledata** | `LittledataLayer` variable | `littledata_layer` |
| | Littledata script | `littledata_script` |
| | `littledata.io` domain reference | `littledata_domain` |
| | Shopify app embed | `littledata_app_embed` |
| **Elevar** | `ElevarDataLayer` variable | `elevar_datalayer` |
| | `ElevarGtmSuite` variable | `elevar_gtm_suite` |
| | Elevar script | `elevar_script` |
| | `getelevar.com` domain reference | `elevar_domain` |

### Error Responses

| Status | Meaning |
|---|---|
| `400` | Missing or invalid `domain` parameter |
| `502` | Could not fetch the website |
| `504` | Website timed out |

## Clay Integration

1. Add an **HTTP API** enrichment column
2. Set method to **GET**
3. Set URL to: `https://your-vercel-app.vercel.app/api/detect?domain={{domain_column}}`
4. Map `uses_klaviyo`, `uses_littledata`, and `uses_elevar` to output columns

## Project Structure

```
api/
  detect.py      # Vercel serverless function — detection endpoint
  index.py       # API documentation page
pipeline/
  detector.py    # Detection functions for pipeline use
vercel.json      # Vercel routing config
```

## Local Development

```bash
pip install -r requirements.txt

# Deploy to Vercel
vercel deploy --prod
```

## Limitations

- Only the initial HTML is analyzed — scripts loaded dynamically via tag managers at runtime won't be detected.
- Only the homepage (`/`) is checked.
- Password-protected or geo-blocked sites may return non-HTML responses.

## Tech Stack

- **Python** with [httpx](https://www.python-httpx.org/) and [BeautifulSoup](https://beautiful-soup-4.readthedocs.io/)
- **Vercel** serverless functions for hosting
