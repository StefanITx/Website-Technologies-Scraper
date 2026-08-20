import re

from config.models import Evidence, Match_Result


# html_body is one raw string - no keys, no fields, so only contains/regex
# make sense here. Returns a full Match_Result for this one signature, or
# None if it did not match this page's html_text.
def match(signature_entry, html_text):
    match_type = signature_entry["match_type"]
    pattern = signature_entry["pattern"]
    matched_text = None

    if match_type == "contains":
        if pattern in html_text:
            matched_text = pattern
    elif match_type == "regex":
        found = re.search(pattern, html_text)
        if found:
            matched_text = found.group(0)

    if matched_text is None:
        return None

    evidence = Evidence(
        source=signature_entry["source"],
        contains=matched_text,
        confidence=signature_entry["confidence"]
    )
    return Match_Result(
        technology=signature_entry["technology"],
        category=signature_entry["category"],
        evidence=[evidence],
        final_confidence=signature_entry["confidence"]
    )
