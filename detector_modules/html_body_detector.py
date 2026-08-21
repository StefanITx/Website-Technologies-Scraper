import re

from config.models import Evidence


# html_body is one raw string - no keys, no fields, so only contains/regex
# make sense here. Returns Evidence for this one source entry, or None if
# it did not match this page's html_text. Technology/category live on the
# parent signature group now, not here - the caller attaches them once,
# after collecting evidence from every source a technology carries.
def match(source_entry, html_text):
    match_type = source_entry["match_type"]
    pattern = source_entry["pattern"]
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

    return Evidence(
        source=source_entry["source"],
        contains=matched_text,
        confidence=source_entry["confidence"]
    )
