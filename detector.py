import json
from dataclasses import asdict

from detector_modules import cookies_detector, headers_detector, html_body_detector

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


# Every module returns its own full Match_Result for one signature - one
# technology, one evidence item. The same technology can legitimately
# match several signatures (from different modules, even), so this
# second, separate pass merges any duplicates into one entry with
# combined evidence and the max confidence across them.
def merge_matches_by_technology(raw_matches):
    result = []

    for match_result in raw_matches:
        existing_technology = None
        for item in result:
            if item["technology"] == match_result.technology:
                existing_technology = item

        if existing_technology is not None:
            new_evidence = asdict(match_result)["evidence"]
            existing_technology["evidence"].extend(new_evidence)
            existing_technology["final_confidence"] = max(
                existing_technology["final_confidence"], match_result.final_confidence
            )
        else:
            result.append(asdict(match_result))

    return result


# Orchestrator only - no match_type logic lives here. For every signature,
# ask the module that owns its source type whether it matches, and simply
# collect whatever comes back. Adding a new source type later
# (robots_txt, dns, ...) means adding one new module and one new elif
# here, not touching the modules that already exist.
def signature_matches(html_text, headers, cookies):
    raw_matches = []
    if signature is None:
        print("No signatures loaded. Exiting signature matching.")
        return raw_matches

    for signature_entry in signature:
        match_result = None

        if signature_entry["source"] == "html_body":
            match_result = html_body_detector.match(signature_entry, html_text)
        elif signature_entry["source"] == "headers":
            match_result = headers_detector.match(signature_entry, headers)
        elif signature_entry["source"] == "cookies":
            match_result = cookies_detector.match(signature_entry, cookies)

        if match_result is not None:
            raw_matches.append(match_result)

    return merge_matches_by_technology(raw_matches)


if __name__ == "__main__":
    data=signature_matches(mock_html, mock_headers,mock_cookies)

    for match in data:
        print(match)
