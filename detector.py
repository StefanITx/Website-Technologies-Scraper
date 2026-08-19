import re
import json
from dataclasses import asdict, dataclass

@dataclass
class Match_Result:
    technology:str
    category:str
    source:str
    contains:str
    confidence:float

signature=None

try:
    with open("signatures.json","r", encoding="utf-8") as f:
        signature=json.load(f)
except FileNotFoundError:
    print("signatures.json file not found. Please ensure the file exists in the current directory.")
except json.JSONDecodeError:
    print("Error decoding signatures.json. Please ensure the file contains valid JSON.")

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
                match_Result=Match_Result(
                    technology=signature[i]["technology"],
                    category=signature[i]["category"],
                    source=signature[i]["source"],
                    contains=con,
                    confidence=signature[i]["confidence"]
                )
                result.append(asdict(match_Result))
                
        elif signature[i]["match_type"]=="regex":
            match=re.search(signature[i]["pattern"], content)
            if match:
                con=f"{content_key}: {match.group(0)}" if content_key else match.group(0)
                match_Result=Match_Result(
                    technology=signature[i]["technology"],
                    category=signature[i]["category"],
                    source=signature[i]["source"],
                    contains=con,
                    confidence=signature[i]["confidence"]
                )
                result.append(asdict(match_Result))
    return result

    