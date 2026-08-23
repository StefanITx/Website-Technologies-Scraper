import glob
import json
import re
import signal

WEBAPP_TECHNOLOGIES_DIRECTORY = "src/technologies"
WEBAPP_CATEGORIES_PATH = "src/categories.json"

REQUIRE_CPE = True
OUTPUT_SIGNATURES_PATH = "signatures.json" if REQUIRE_CPE else "signatures_no_cpe_experiment.json"

HEADERS_SOURCE_CONFIDENCE = 0.85
COOKIES_SOURCE_CONFIDENCE = 0.75
META_GENERATOR_CONFIDENCE = 0.90
SCRIPT_SOURCE_CONFIDENCE = 0.80
HTML_BODY_CONFIDENCE = 0.75

UNESCAPED_REGEX_METACHARACTER_PATTERN = re.compile(r'(?<!\\)[\[\]\(\)\+\*\?\{\}\|\^\$]')
REGEX_ESCAPE_CLASS_PATTERN = re.compile(r'\\[dDsSwWbB]')

REGEX_SAFETY_TEST_STRING = "qwertyuiopasdfghjklzxcvbnm" * 4000
REGEX_SAFETY_TIMEOUT_SECONDS = 1
DROPPED_UNSAFE_REGEX_PATTERNS = []


class RegexSafetyTimeout(Exception):
    pass


def raise_regex_safety_timeout(signum, frame):
    raise RegexSafetyTimeout()


def pattern_is_regex_safe(technology_name, pattern_text):
    signal.signal(signal.SIGALRM, raise_regex_safety_timeout)
    signal.alarm(REGEX_SAFETY_TIMEOUT_SECONDS)
    try:
        re.search(pattern_text, REGEX_SAFETY_TEST_STRING)
        return True
    except RegexSafetyTimeout:
        DROPPED_UNSAFE_REGEX_PATTERNS.append((technology_name, pattern_text))
        return False
    finally:
        signal.alarm(0)


def strip_webapp_suffix(raw_pattern):
    return raw_pattern.split("\\;")[0]


def pattern_looks_like_regex(pattern_text):
    return bool(
        UNESCAPED_REGEX_METACHARACTER_PATTERN.search(pattern_text)
        or REGEX_ESCAPE_CLASS_PATTERN.search(pattern_text)
    )


def pattern_is_valid_regex(pattern_text):
    try:
        re.compile(pattern_text)
        return True
    except re.error:
        return False


def unescape_literal_pattern(pattern_text):
    return re.sub(r'\\(.)', r'\1', pattern_text)


def strip_literal_anchors(pattern_text):
    if pattern_text.startswith("^"):
        pattern_text = pattern_text[1:]
    if pattern_text.endswith("$"):
        pattern_text = pattern_text[:-1]
    return pattern_text


def classify_match_type_and_pattern(raw_pattern):
    pattern_text = strip_webapp_suffix(raw_pattern)

    if pattern_text == "":
        return "exists", None

    if pattern_is_valid_regex(pattern_text) and pattern_looks_like_regex(pattern_text):
        return "regex", pattern_text

    literal_pattern = unescape_literal_pattern(strip_literal_anchors(pattern_text))
    return "contains", literal_pattern


def resolve_category(category_ids, categories_json):
    if not category_ids:
        return None

    most_primary_category_id = min(
        category_ids,
        key=lambda category_id: categories_json[str(category_id)]["priority"],
    )
    raw_category_name = categories_json[str(most_primary_category_id)]["name"]
    lowercase_name = raw_category_name.lower()
    return re.sub(r'[^a-z0-9]+', '_', lowercase_name).strip('_')


def build_dict_field_sources(field_values, source_name, base_confidence):
    source_entries = []

    for field_name, raw_pattern in field_values.items():
        if pattern_is_valid_regex(field_name) and pattern_looks_like_regex(field_name):
            source_entries.append({
                "source": source_name,
                "match_type": "key_regex",
                "pattern": field_name,
                "confidence": base_confidence,
            })
            continue

        match_type, pattern_text = classify_match_type_and_pattern(raw_pattern)
        source_entry = {
            "source": source_name,
            "field": field_name,
            "match_type": match_type,
            "confidence": base_confidence,
        }
        if pattern_text is not None:
            source_entry["pattern"] = pattern_text
        source_entries.append(source_entry)

    return source_entries


def build_html_body_pattern_sources(raw_patterns, base_confidence):
    source_entries = []

    for raw_pattern in raw_patterns:
        match_type, pattern_text = classify_match_type_and_pattern(raw_pattern)
        if match_type == "exists":
            continue
        source_entries.append({
            "source": "html_body",
            "match_type": match_type,
            "pattern": pattern_text,
            "confidence": base_confidence,
        })

    return source_entries


def build_meta_generator_sources(meta_values, base_confidence):
    source_entries = []

    for meta_name, raw_pattern in meta_values.items():
        stripped_pattern = strip_webapp_suffix(raw_pattern)
        if stripped_pattern.startswith("^"):
            stripped_pattern = stripped_pattern[1:]

        match_type, pattern_text = classify_match_type_and_pattern(stripped_pattern)
        if match_type == "exists":
            continue

        value_pattern = pattern_text if match_type == "regex" else re.escape(pattern_text)
        escaped_meta_name = re.escape(meta_name)
        name_then_content = f'name="{escaped_meta_name}"[^>]*content="{value_pattern}"'
        content_then_name = f'content="{value_pattern}"[^>]*name="{escaped_meta_name}"'
        same_tag_pattern = f'(?i)<meta[^>]*(?:{name_then_content}|{content_then_name})[^>]*>'

        source_entries.append({
            "source": "html_body",
            "match_type": "regex",
            "pattern": same_tag_pattern,
            "confidence": base_confidence,
        })

    return source_entries


def as_list_field(entry, field_name):
    value = entry.get(field_name)
    return value if isinstance(value, list) else []


def build_sources_for_technology(entry):
    sources = []

    headers = entry.get("headers")
    if isinstance(headers, dict):
        sources.extend(build_dict_field_sources(headers, "headers", HEADERS_SOURCE_CONFIDENCE))

    cookies = entry.get("cookies")
    if isinstance(cookies, dict):
        sources.extend(build_dict_field_sources(cookies, "cookies", COOKIES_SOURCE_CONFIDENCE))

    meta = entry.get("meta")
    if isinstance(meta, dict):
        sources.extend(build_meta_generator_sources(meta, META_GENERATOR_CONFIDENCE))

    html_patterns = as_list_field(entry, "html")
    if html_patterns:
        sources.extend(build_html_body_pattern_sources(html_patterns, HTML_BODY_CONFIDENCE))

    script_patterns = as_list_field(entry, "scriptSrc") + as_list_field(entry, "scripts")
    if script_patterns:
        sources.extend(build_html_body_pattern_sources(script_patterns, SCRIPT_SOURCE_CONFIDENCE))

    return sources


HARDCODED_DNS_SOURCES_BY_TECHNOLOGY = {
    "Cloudflare": [
        {"source": "dns", "field": "name_servers", "match_type": "contains", "pattern": ".cloudflare.com", "confidence": 0.8},
        {"source": "dns", "field": "start_of_authority", "match_type": "contains", "pattern": ".cloudflare.com", "confidence": 0.8},
        {"source": "dns", "field": "txt_records", "match_type": "contains", "pattern": "cloudflare_dashboard_sso=", "confidence": 0.85},
    ],
    "Docker": [
        {"source": "dns", "field": "txt_records", "match_type": "contains", "pattern": "docker-verification=", "confidence": 0.85},
    ],
    "Hostinger": [
        {"source": "dns", "field": "start_of_authority", "match_type": "regex", "pattern": "\\.(?:dns-parking|hostinger)\\.com", "confidence": 0.8},
    ],
    "MailChimp": [
        {"source": "dns", "field": "txt_records", "match_type": "contains", "pattern": "spf.mandrillapp.com", "confidence": 0.8},
    ],
    "Salesforce": [
        {"source": "dns", "field": "txt_records", "match_type": "contains", "pattern": "salesforce.com", "confidence": 0.85},
        {"source": "dns", "field": "txt_records", "match_type": "regex", "pattern": "^00D[A-Za-z0-9]{12}=", "confidence": 0.75},
    ],
    "Stripe": [
        {"source": "dns", "field": "txt_records", "match_type": "contains", "pattern": "stripe-verification=", "confidence": 0.85},
    ],
}

HARDCODED_DNS_ONLY_TECHNOLOGIES = [
    {"technology": "Dropbox", "category": "digital_asset_management", "sources": [
        {"source": "dns", "field": "txt_records", "match_type": "contains", "pattern": "dropbox-domain-verification", "confidence": 0.85},
    ]},
    {"technology": "Imgix", "category": "cdn", "sources": [
        {"source": "dns", "field": "start_of_authority", "match_type": "contains", "pattern": ".imgix.net", "confidence": 0.8},
    ]},
    {"technology": "Keybase", "category": "security", "sources": [
        {"source": "dns", "field": "txt_records", "match_type": "contains", "pattern": "keybase-site-verification", "confidence": 0.85},
    ]},
    {"technology": "Notion", "category": "page_builders", "sources": [
        {"source": "dns", "field": "txt_records", "match_type": "contains", "pattern": "notion-domain-verification=", "confidence": 0.85},
    ]},
]


def merge_hardcoded_dns_technologies(technologies):
    by_name = {technology["technology"]: technology for technology in technologies}

    for name, dns_sources in HARDCODED_DNS_SOURCES_BY_TECHNOLOGY.items():
        if name in by_name:
            by_name[name]["sources"].extend(dns_sources)

    technologies.extend(HARDCODED_DNS_ONLY_TECHNOLOGIES)
    return technologies


def main():
    with open(WEBAPP_CATEGORIES_PATH, encoding="utf-8") as categories_file:
        categories_json = json.load(categories_file)

    technologies = []
    skipped_no_cpe_count = 0
    skipped_no_category_at_all_count = 0
    skipped_no_usable_source_names = []

    for path in sorted(glob.glob(f"{WEBAPP_TECHNOLOGIES_DIRECTORY}/*.json")):
        with open(path, encoding="utf-8") as technologies_file:
            entries = json.load(technologies_file)

        for technology_name, entry in entries.items():
            if REQUIRE_CPE and "cpe" not in entry:
                skipped_no_cpe_count += 1
                continue

            category = resolve_category(entry.get("cats", []), categories_json)
            if category is None:
                skipped_no_category_at_all_count += 1
                continue

            sources = build_sources_for_technology(entry)
            sources = [
                source_entry for source_entry in sources
                if source_entry["match_type"] not in ("regex", "key_regex")
                or pattern_is_regex_safe(technology_name, source_entry["pattern"])
            ]
            if not sources:
                skipped_no_usable_source_names.append(technology_name)
                continue

            technologies.append({
                "technology": technology_name,
                "category": category,
                "sources": sources,
            })

    technologies = merge_hardcoded_dns_technologies(technologies)

    with open(OUTPUT_SIGNATURES_PATH, "w", encoding="utf-8") as output_file:
        json.dump(technologies, output_file, indent=2)
        output_file.write("\n")

    total_source_entries = sum(len(technology["sources"]) for technology in technologies)
    total_technologies_scanned = (
        len(technologies)
        + skipped_no_cpe_count
        + skipped_no_category_at_all_count
        + len(skipped_no_usable_source_names)
    )

    print(f"total technologies scanned in webappanalyzer: {total_technologies_scanned}")
    print(f"technologies lost - no cpe identifier: {skipped_no_cpe_count}")
    print(f"technologies lost - cpe present but zero category ids at all: {skipped_no_category_at_all_count}")
    print(f"technologies lost - cpe and category ok, but only js/dom signal (unreachable): {len(skipped_no_usable_source_names)}")
    print(f"technologies written to {OUTPUT_SIGNATURES_PATH}: {len(technologies)}")
    print(f"total source entries across those technologies: {total_source_entries}")
    print(f"regex patterns dropped for catastrophic-backtracking risk: {len(DROPPED_UNSAFE_REGEX_PATTERNS)}")
    for technology_name, pattern in DROPPED_UNSAFE_REGEX_PATTERNS:
        print(f"  {technology_name}: {pattern}")
    print()
    print("technologies lost to js/dom-only signal:")
    for name in skipped_no_usable_source_names:
        print(f"  {name}")


if __name__ == "__main__":
    main()
