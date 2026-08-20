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



def signature_matches(html_text,headers):
    result=[]
    if signature is None:
        print("No signatures loaded. Exiting signature matching.")
        return result
    for i in range(0, len(signature)):
        content=""
        content_key=None
        if signature[i]["source"]=="html_body":
            content=html_text
        elif signature[i]["source"]=="headers":
            content=headers.get(signature[i]["field"], "")
            content_key=signature[i]["field"]


        if signature[i]["match_type"]=="contains":
            if signature[i]["pattern"] in content:
                con=f"{content_key}: {content}" if content_key else signature[i]["pattern"]

                evidence =Evidence(
                    source=signature[i]["source"],
                    contains=con,
                    confidence=signature[i]["confidence"]
                )

                found=False
                for item in result:
                    if item["technology"] == signature[i]["technology"]:
                        item["evidence"].append(asdict(evidence))
                        item["final_confidence"] = max(item["final_confidence"], signature[i]["confidence"])
                        found=True
                        break

                if not found:
                    match_Result=Match_Result(
                        technology=signature[i]["technology"],
                        category=signature[i]["category"],
                        evidence=[asdict(evidence)],
                        final_confidence=signature[i]["confidence"]
                    )
                    result.append(asdict(match_Result))
                
        elif signature[i]["match_type"]=="regex":
            match=re.search(signature[i]["pattern"], content)
            if match:
                con=f"{content_key}: {match.group(0)}" if content_key else match.group(0)
                evidence =Evidence(
                    source=signature[i]["source"],
                    contains=con,
                    confidence=signature[i]["confidence"]
                )
                found=False
                for item in result:
                    if item["technology"] == signature[i]["technology"]:
                        item["evidence"].append(asdict(evidence))
                        item["final_confidence"] = max(item["final_confidence"], signature[i]["confidence"])
                        found=True
                        break
                if not found:
                    match_Result=Match_Result(
                        technology=signature[i]["technology"],
                        category=signature[i]["category"],
                        evidence=[asdict(evidence)],
                        final_confidence=signature[i]["confidence"]
                    )
                    result.append(asdict(match_Result))
                
    return result

if __name__ == "__main__":
    x=signature_matches(mock_html, mock_headers)

    for match in x:
        print(match)