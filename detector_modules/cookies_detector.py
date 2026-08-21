import re

from config.models import Evidence


# Cookie values are usually meaningless random tokens, so evidence hides
# the value behind "[...]" and only shows which cookie matched. Returns
# Evidence for this one source entry, or None if it did not match.
# Technology/category live on the parent signature group now, not here -
# the caller attaches them once, after collecting evidence from every
# source a technology carries.
def match(source_entry, cookies):
    match_type = source_entry["match_type"]
    evidence_text = None

    # key_regex has no "field" - some cookies (Drupal, Wordfence) use a
    # per-site hash as part of the name, so there is no fixed key to look
    # up. This checks every real cookie name the domain actually sent.
    if match_type == "key_regex":
        pattern = source_entry["pattern"]
        for key in cookies:
            if re.search(pattern, key):
                evidence_text = key
                break
    else:
        field = source_entry.get("field")
        content = cookies.get(field, None) if field is not None else None

        if content is not None:
            if match_type == "exists":
                evidence_text = f"{field}: [...]"
            elif match_type == "contains":
                if source_entry["pattern"] in content:
                    evidence_text = f"{field}: [...]"
            elif match_type == "regex":
                if re.search(source_entry["pattern"], content):
                    evidence_text = f"{field}: [...]"

    if evidence_text is None:
        return None

    return Evidence(
        source=source_entry["source"],
        contains=evidence_text,
        confidence=source_entry["confidence"]
    )
