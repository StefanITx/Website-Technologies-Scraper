import json
from dataclasses import asdict

from config.models import MatchResult
from detector_modules import cookies_detector, headers_detector, html_body_detector, dns_detector

signature=None

try:
    with open("signatures.json","r", encoding="utf-8") as f:
        signature=json.load(f)
except FileNotFoundError:
    print("signatures.json file not found. Please ensure the file exists in the current directory.")
except json.JSONDecodeError:
    print("Error decoding signatures.json. Please ensure the file contains valid JSON.")

mock_html = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="generator" content="WordPress 6.4.3" />
    <title>Sample WordPress Page</title>
    <link rel="stylesheet" href="https://example.com/wp-content/themes/twentytwentyfour/style.css" />
  </head>
  <body>
    <header>
      <h1>Welcome to my site</h1>
    </header>
    <main>
      <p>This page is powered by WordPress and uses the wp-content directory.</p>
      <a href="https://example.com/wp-admin">Admin</a>
    </main>
  </body>
</html>
"""

mock_headers = {
    "server": "Squarespace",
    "x-powered-by": "PHP/7.4.3",
    "x-nginx-cache": "WordPress",
}

mock_cookies={
    "__cf_bm": "GGDs5laA5XMqPJJRSQle2MABPY2x3d6PfM8wdsqJUWI-1787188943.1781182-1.0.1.1-y8SwY5kZXAT1HewAJ4nafeIiuEMotlwreCuh8fgiV8QKiU2H4x16zAXb93sgPFpTCmiDsrGiF77GEvYGk0M7mQOoq5xdJ._z4TX4prAU9jEXPwtxBI43_ywz6TAmq95C",
    "_shopify_essential": ":AaAcw0FuAAEAZb1_p-hNNne3IxweH_2v7dHICsMJoH12DoJiOT1OWRvOJfL18mkZADENYWgdLY3XucLaWS2N3cBgFvjX04_SC4zF6VBSR-feAJXOdDi0LnMz5p5gdORHjCGpDswuGIyeYloZnry0E23RBzwGEGiLEzcOwLivZcJnQy_XCiQbQp6MMOfO2kyeiSyM4YOljyMPKIgb6FgGGn23FhEgP_GBSa5gcnruOO38AXPPqLO8jjPasqXraIEUcTYXlhqoLEbrHI3681xRECyzj-x2UxCiUZlwrNRpqreS16gkNSMJKRYJmTntgE5uF1hKZRRj1p260nM20T9fZcNN8RMRjRSLh6d3UcCGc-UsuBjF-YBEZQ0pEjNh0h6UDMFBXQBWEDx6m0lLJt8v8LGb1enbAryNi4ouKZHR5lJkrMzJZQEIYZobDUG6IhUUmfuLrVev3mhCuU2BJgJe1SuBoH7XEjaNWOG64UJ5gIk94IGKgmum_HZ8dkofpMCpdF-20sDOy5uFLpHDjQm0nLzQ5C45QBKr:",
    "cart_currency": "JPY",
    "ssr-caching": "cache#desc=hit#varnish=hit_hit#dc#desc=fastly_g",
    "sec-fetch-unsupported": "1",
    "PHPSESSID": "82uf6t3vvk4somaa78dmfsb48d"
}


# Orchestrator only - no match_type logic lives here. signatures.json is
# grouped one object per technology, each carrying a "sources" list, so a
# technology's evidence is already together in the input - no separate
# merge-by-technology pass needed afterward. For every source entry, ask
# the module that owns its source type whether it matches, and collect
# whatever Evidence comes back. Adding a new source type later (robots_txt,
# dns, ...) means adding one new module and one new elif here, not
# touching the modules that already exist.
def signature_matches(html_text, headers, cookies,dns_result):
    results = []
    if signature is None:
        print("No signatures loaded. Exiting signature matching.")
        return results

    for technology_entry in signature:
        evidence_list = []

        for source_entry in technology_entry["sources"]:
            evidence = None

            if source_entry["source"] == "html_body":
                evidence = html_body_detector.match(source_entry, html_text)
            elif source_entry["source"] == "headers":
                evidence = headers_detector.match(source_entry, headers)
            elif source_entry["source"] == "cookies":
                evidence = cookies_detector.match(source_entry, cookies)
            elif source_entry["source"] == "dns" and dns_result is not None:
                evidence = dns_detector.match(source_entry, dns_result)

            if evidence is not None:
                evidence_list.append(evidence)

        if evidence_list:
            final_confidence = max(evidence.confidence for evidence in evidence_list)
            results.append(asdict(MatchResult(
                technology=technology_entry["technology"],
                category=technology_entry["category"],
                evidence=evidence_list,
                final_confidence=final_confidence
            )))

    return results


if __name__ == "__main__":
    data=signature_matches(mock_html, mock_headers,mock_cookies,None)

    for match in data:
        print(match)
