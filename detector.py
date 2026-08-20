import re
import json
from dataclasses import asdict, dataclass


@dataclass
class Evidence:
    source:str
    contains:str
    confidence:float
@dataclass
class Match_Result:
    technology:str
    category:str
    evidence:list[Evidence]
    final_confidence: float

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


def build_evidence_text(source, field, content, matched_text):
    if source == "html_body":
        return matched_text

    if source == "headers":
        evidence_text = field
        evidence_text = evidence_text + ": "
        evidence_text = evidence_text + content
        return evidence_text

    if source == "cookies":
        evidence_text = field
        evidence_text = evidence_text + ": [...]"
        return evidence_text

    return matched_text


def record_match(result, signature_entry, evidence_text):
    evidence = Evidence(
        source=signature_entry["source"],
        contains=evidence_text,
        confidence=signature_entry["confidence"]
    )

    existing_technology = None
    for item in result:
        if item["technology"] == signature_entry["technology"]:
            existing_technology = item

    if existing_technology is not None:
        existing_technology["evidence"].append(asdict(evidence))
        updated_confidence = max(existing_technology["final_confidence"], signature_entry["confidence"])
        existing_technology["final_confidence"] = updated_confidence
        return

    match_Result = Match_Result(
        technology=signature_entry["technology"],
        category=signature_entry["category"],
        evidence=[asdict(evidence)],
        final_confidence=signature_entry["confidence"]
    )
    result.append(asdict(match_Result))


def signature_matches(html_text, headers, cookies):
    result = []
    if signature is None:
        print("No signatures loaded. Exiting signature matching.")
        return result

    for i in range(0, len(signature)):
        content = ""
        content_key = None

        if signature[i]["source"] == "html_body":
            content = html_text
        elif signature[i]["source"] == "headers":
            content = headers.get(signature[i]["field"], None)
            content_key = signature[i]["field"]
        elif signature[i]["source"] == "cookies":
            content = cookies.get(signature[i]["field"], None)
            content_key = signature[i]["field"]

        if signature[i]["match_type"] == "exists":
            if content is not None:
                evidence_text = build_evidence_text(signature[i]["source"], content_key, content, content)
                record_match(result, signature[i], evidence_text)

        elif signature[i]["match_type"] == "contains":
            if content is not None and signature[i]["pattern"] in content:
                evidence_text = build_evidence_text(signature[i]["source"], content_key, content, signature[i]["pattern"])
                record_match(result, signature[i], evidence_text)

        elif signature[i]["match_type"] == "regex":
            if content is not None:
                match = re.search(signature[i]["pattern"], content)
                if match:
                    evidence_text = build_evidence_text(signature[i]["source"], content_key, content, match.group(0))
                    record_match(result, signature[i], evidence_text)

    return result

if __name__ == "__main__":
    data=signature_matches(mock_html, mock_headers,mock_cookies)

    for match in data:
        print(match)

