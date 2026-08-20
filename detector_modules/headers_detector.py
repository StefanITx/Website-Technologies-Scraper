import re

from config.models import Evidence, Match_Result


# Header values are usually meaningful (a real string, not a random
# token), so evidence shows the actual value, unlike cookies_detector.
# Returns a full Match_Result for this one signature, or None if it did
# not match.
def match(signature_entry, headers):
    match_type = signature_entry["match_type"]
    evidence_text = None

    # key_regex has no "field" - same idea as cookies_detector, for a
    # header whose name is not fixed. Not known to be needed yet, kept
    # symmetric with cookies_detector since the mechanism is the same.
    if match_type == "key_regex":
        pattern = signature_entry["pattern"]
        for key in headers:
            if re.search(pattern, key):
                evidence_text = key
                break
    else:
        field = signature_entry.get("field")
        content = headers.get(field, None) if field is not None else None

        if content is not None:
            if match_type == "exists":
                evidence_text = f"{field}: {content}"
            elif match_type == "contains":
                if signature_entry["pattern"] in content:
                    evidence_text = f"{field}: {content}"
            elif match_type == "regex":
                found = re.search(signature_entry["pattern"], content)
                if found:
                    evidence_text = f"{field}: {found.group(0)}"

    if evidence_text is None:
        return None

    evidence = Evidence(
        source=signature_entry["source"],
        contains=evidence_text,
        confidence=signature_entry["confidence"]
    )
    return Match_Result(
        technology=signature_entry["technology"],
        category=signature_entry["category"],
        evidence=[evidence],
        final_confidence=signature_entry["confidence"]
    )
