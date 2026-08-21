import re

from config.models import Evidence


# Header values are usually meaningful (a real string, not a random
# token), so evidence shows the actual value, unlike cookies_detector.
# Returns Evidence for this one source entry, or None if it did not
# match. Technology/category live on the parent signature group now, not
# here - the caller attaches them once, after collecting evidence from
# every source a technology carries.
def match(source_entry, headers):
    match_type = source_entry["match_type"]
    evidence_text = None

    # key_regex has no "field" - same idea as cookies_detector, for a
    # header whose name is not fixed. Not known to be needed yet, kept
    # symmetric with cookies_detector since the mechanism is the same.
    if match_type == "key_regex":
        pattern = source_entry["pattern"]
        for key in headers:
            if re.search(pattern, key):
                evidence_text = key
                break
    else:
        field = source_entry.get("field")
        content = headers.get(field, None) if field is not None else None

        if content is not None:
            if match_type == "exists":
                evidence_text = f"{field}: {content}"
            elif match_type == "contains":
                if source_entry["pattern"] in content:
                    evidence_text = f"{field}: {content}"
            elif match_type == "regex":
                found = re.search(source_entry["pattern"], content)
                if found:
                    evidence_text = f"{field}: {found.group(0)}"

    if evidence_text is None:
        return None

    return Evidence(
        source=source_entry["source"],
        contains=evidence_text,
        confidence=source_entry["confidence"]
    )
