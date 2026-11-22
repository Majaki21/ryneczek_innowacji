import re

STOP_WORDS = {
    "jest", "który", "która", "które", "oraz", "przez", "przy", "tego",
    "zespół", "potrzebuje", "potrzebujemy", "chcemy", "można",
}


def terms(text):
    words = re.findall(r"[^\W\d_]{4,}", text.casefold())
    return {word[:5]: word for word in words if word not in STOP_WORDS}


def labels(values):
    return {value.strip().casefold(): value.strip() for value in values}


def match(item, text, tags):
    shared_tags = sorted(labels(item["tags"]).keys() & labels(tags).keys())
    query_terms = terms(text)
    shared_words = [query_terms[key] for key in sorted(query_terms.keys() & terms(item["summary"]).keys())]
    reasons = []
    if shared_tags:
        reasons.append("Wspólne tagi: " + ", ".join(shared_tags))
    if shared_words:
        reasons.append("Zbieżne słowa w opisie problemu: " + ", ".join(shared_words))
    return 3 * len(shared_tags) + len(shared_words), reasons


def similar(item, catalog):
    results = []
    for other in catalog:
        if other["id"] == item["id"]:
            continue
        score, reasons = match(other, item["summary"], item["tags"])
        if score:
            results.append({"id": other["id"], "title": other["title"], "reasons": reasons, "score": score})
    return sorted(results, key=lambda row: (-row["score"], row["title"]))[:5]


def need_matches(need, catalog, requester):
    results = []
    available = labels(need["available_conditions"])
    for item in catalog:
        score, reasons = match(item, f"{need['title']} {need['description']}", [need["tag"]])
        if not score:
            continue
        required = labels(item["condition_tags"])
        covered = [required[key] for key in required if key in available]
        pending = [required[key] for key in required if key not in available]
        if covered:
            reasons.append("Zadeklarowane warunki: " + ", ".join(covered))
        if pending:
            reasons.append("Warunki do uzgodnienia: " + ", ".join(pending))
        elif not required:
            reasons.append("Brak listy warunków do porównania. Sprawdź zakres z partnerem.")
        partners = [link for link in item["links"] if link["profile"] != requester]
        recipient = next((link for link in partners if link["role"] == "twórca"), None)
        recipient = recipient or next(iter(partners), None)
        results.append({
            **item, "reason": ". ".join(reasons), "reasons": reasons,
            "score": score + len(covered), "pilot_recipient": recipient,
        })
    return sorted(results, key=lambda row: (-row["score"], row["title"]))
