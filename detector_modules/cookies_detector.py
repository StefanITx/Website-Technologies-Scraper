import re

from config.models import Evidence, Match_Result


# Cookie values are usually meaningless random tokens, so evidence hides
# the value behind "[...]" and only shows which cookie matched. Returns a
# full Match_Result for this one signature, or None if it did not match.
def match(signature_entry, cookies):
    match_type = signature_entry["match_type"]
    evidence_text = None

    # key_regex has no "field" - some cookies (Drupal, Wordfence) use a
    # per-site hash as part of the name, so there is no fixed key to look
    # up. This checks every real cookie name the domain actually sent.
    if match_type == "key_regex":
        pattern = signature_entry["pattern"]
        for key in cookies:
            if re.search(pattern, key):
                evidence_text = key
                break
    else:
        field = signature_entry.get("field")
        content = cookies.get(field, None) if field is not None else None

        if content is not None:
            if match_type == "exists":
                evidence_text = f"{field}: [...]"
            elif match_type == "contains":
                if signature_entry["pattern"] in content:
                    evidence_text = f"{field}: [...]"
            elif match_type == "regex":
                if re.search(signature_entry["pattern"], content):
                    evidence_text = f"{field}: [...]"

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
