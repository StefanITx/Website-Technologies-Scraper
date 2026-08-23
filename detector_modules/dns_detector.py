import re
from dataclasses import asdict

from config.models import Evidence

def match(source_entry, dns_result):
    match_type = source_entry["match_type"]
    evidence_text = None
    pattern = source_entry["pattern"]
    dns_dict=asdict(dns_result)

    if match_type == "regex":
        found=False
        for key,value in dns_dict.items():
            if key != source_entry["field"]:
                continue
            for v in value:
                if re.search(pattern, v):
                    evidence_text = f"{key}: {value}"
                    found=True
                    break
                if found:break
    elif match_type == "contains":
        found = False
        for key,value in dns_dict.items():
            if key != source_entry["field"]:
                continue
            for v in value:
                if pattern in v:
                    evidence_text = f"{key}: {value}"
                    found=True
                    break
                if found:break

    if evidence_text is None:
        return None

    return Evidence(
        source=source_entry["source"],
        contains=evidence_text,
        confidence=source_entry["confidence"]
    )