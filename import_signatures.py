import glob
import json
import re

WEBAPP_TECHNOLOGIES_DIRECTORY = "src/technologies"
WEBAPP_CATEGORIES_PATH = "src/categories.json"
OUTPUT_SIGNATURES_PATH = "signatures.json"

HEADERS_SOURCE_CONFIDENCE = 0.85
COOKIES_SOURCE_CONFIDENCE = 0.75
META_GENERATOR_CONFIDENCE = 0.90
SCRIPT_SOURCE_CONFIDENCE = 0.80
HTML_BODY_CONFIDENCE = 0.75

WEBAPP_CATEGORY_ID_TO_TAXONOMY = {
    1: "cms",
    6: "ecommerce_platform",
    10: "analytics",
    12: "javascript_framework",
    16: "security_ssl",
    17: "font_service",
    18: "web_framework",
    22: "web_server",
    23: "caching",
    31: "cdn",
    32: "marketing_tag_manager",
    41: "payment_processor",
    42: "marketing_tag_manager",
    51: "plugin",
    52: "customer_support",
    53: "customer_support",
    54: "plugin",
    59: "javascript_framework",
    66: "css_framework",
    67: "security_ssl",
    69: "security_ssl",
    70: "security_ssl",
    75: "email_marketing",
    80: "plugin",
    87: "plugin",
    88: "hosting_provider",
    90: "plugin",
    100: "plugin",
}

UNESCAPED_REGEX_METACHARACTER_PATTERN = re.compile(r'(?<!\\)[\[\]\(\)\+\*\?\{\}\|\^\$]')
REGEX_ESCAPE_CLASS_PATTERN = re.compile(r'\\[dDsSwWbB]')


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


def format_category_name_as_taxonomy_string(category_name):
    lowercase_name = category_name.lower()
    return re.sub(r'[^a-z0-9]+', '_', lowercase_name).strip('_')


def fall_back_to_webapp_category_name(category_ids, categories_json):
    if not category_ids:
        return None

    most_primary_category_id = min(
        category_ids,
        key=lambda category_id: categories_json[str(category_id)]["priority"],
    )
    raw_category_name = categories_json[str(most_primary_category_id)]["name"]
    return format_category_name_as_taxonomy_string(raw_category_name)


def resolve_category(category_ids, categories_json):
    mapped_categories = set()
    for category_id in category_ids:
        taxonomy_name = WEBAPP_CATEGORY_ID_TO_TAXONOMY.get(category_id)
        if taxonomy_name is not None:
            mapped_categories.add(taxonomy_name)

    if not mapped_categories:
        return fall_back_to_webapp_category_name(category_ids, categories_json)

    if len(mapped_categories) == 1:
        return next(iter(mapped_categories))

    def lowest_priority_for_category(taxonomy_name):
        matching_priorities = [
            categories_json[str(category_id)]["priority"]
            for category_id in category_ids
            if WEBAPP_CATEGORY_ID_TO_TAXONOMY.get(category_id) == taxonomy_name
        ]
        return min(matching_priorities)

    return min(mapped_categories, key=lowest_priority_for_category)


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
        pattern_text = strip_webapp_suffix(raw_pattern)
        if pattern_text == "":
            continue

        if pattern_text.startswith("^"):
            pattern_text = pattern_text[1:]

        if pattern_is_valid_regex(pattern_text) and pattern_looks_like_regex(pattern_text):
            value_pattern = pattern_text
        else:
            literal_value = unescape_literal_pattern(strip_literal_anchors(pattern_text))
            value_pattern = re.escape(literal_value)

        escaped_meta_name = re.escape(meta_name)
        name_then_content = f'name="{escaped_meta_name}"[^>]*content="{value_pattern}"'
        content_then_name = f'content="{value_pattern}"[^>]*name="{escaped_meta_name}"'
        same_tag_pattern = f'<meta[^>]*(?:{name_then_content}|{content_then_name})[^>]*>'

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
            if "cpe" not in entry:
                skipped_no_cpe_count += 1
                continue

            category = resolve_category(entry.get("cats", []), categories_json)
            if category is None:
                skipped_no_category_at_all_count += 1
                continue

            sources = build_sources_for_technology(entry)
            if not sources:
                skipped_no_usable_source_names.append(technology_name)
                continue

            technologies.append({
                "technology": technology_name,
                "category": category,
                "sources": sources,
            })

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
    print(f"technologies written to signatures.json: {len(technologies)}")
    print(f"total source entries across those technologies: {total_source_entries}")
    print()
    print("technologies lost to js/dom-only signal:")
    for name in skipped_no_usable_source_names:
        print(f"  {name}")


if __name__ == "__main__":
    main()
