from __future__ import annotations

import re
from collections.abc import Callable

from ruleatlas_contracts.classification.scaffold_markers import (
    _CONTRACT_CANT,
    _CONTRACT_MUST_NOT,
    ASSERT_EXPECT_PATTERN,
    BARE_ASSERT_PATTERN,
    BASE_URL_LITERAL_PATTERN,
    CSHARP_USING_PATTERN,
    DOMAIN_BEHAVIOR_KEYWORDS,
    DOMAIN_SYMBOL_USAGE_PATTERN,
    ENUM_MEMBER_PATTERN,
    FRAMEWORK_MODULE_MARKERS,
    FUNCTION_SIGNATURE_PATTERN,
    GENERIC_BDD_SETUP_STEPS,
    GENERIC_EXPECT_PATTERN,
    GENERIC_RENDER_PATTERN,
    GENERIC_RENDER_PHRASES,
    GENERIC_SMOKE_TEST_TITLES,
    GO_IMPORT_PATTERN,
    GO_IMPORT_STRING_PATTERN,
    GRID_CALLBACK_MARKERS,
    HEALTH_PLATFORM_BDD_MARKERS,
    HOOK_ARROW_PATTERN,
    HOOK_OR_QUERY_HELPER_MARKERS,
    IMPLEMENTATION_PLUMBING_PHRASES,
    IMPORT_LINE_PATTERN,
    JAVA_KOTLIN_IMPORT_PATTERN,
    JS_IT_TEST_PATTERN,
    JS_TEST_NAME_PATTERN,
    JSX_ONLY_PATTERN,
    LIFECYCLE_HOOK_PATTERN,
    MESSAGE_CONSTANT_PATTERN,
    MOCK_SETUP_PATTERN,
    MONKEYPATCH_PATTERN,
    PACKAGE_MARKER_PATH_PATTERN,
    PARAM_ANNOTATION_ONLY_PATTERN,
    PHP_USE_PATTERN,
    PYDANTIC_CLASS_PATTERN,
    PYTHON_IMPORT_PATTERN,
    PYTHON_TEST_BLOCK_PATTERN,
    PYTHON_TEST_DEF_PATTERN,
    RENDER_CALL_PATTERN,
    RENDER_HELPER_PATTERN,
    RETURNS_NULL_UNDEFINED_PATTERN,
    ROUTER_PLUMBING_PATTERN,
    RUBY_REQUIRE_PATTERN,
    SELECTOR_PATTERN,
    STATUS_CODE_ONLY_PATTERN,
    STATUS_CODE_PATTERN,
    STATUS_OK_LITERAL_PATTERN,
    STRONG_PRODUCT_BEHAVIOR_KEYWORDS,
    TECHNICAL_HELPER_PATH_MARKERS,
    TECHNICAL_HELPER_TEST_NAME_MARKERS,
    THIN_MODULE_DOC_MARKERS,
    TYPE_ALIAS_PATTERN,
    TYPE_DECLARATION_PATTERN,
    UPPER_DOMAIN_CONSTANT_PATTERN,
    match_bdd_step,
)
from ruleatlas_contracts.enums import ExtractionSkipReason

__all__ = [
    "classify_line_skip_reason",
    "classify_test_skip_reason",
    "find_domain_test_blocks",
    "find_test_evidence_lines",
    "has_domain_behavior_signal",
    "has_strong_product_behavior_signal",
    "is_domain_symbol_usage_line",
    "is_import_declaration_line",
    "is_non_business_rule_scaffold_line",
    "is_package_marker_path",
    "is_potential_business_behavior_line",
    "is_scaffold_evidence_text",
]


def _is_comment_or_blank_line(stripped: str) -> bool:
    if not stripped or stripped.startswith(("//", "#")):
        return True
    return stripped.startswith(("*", "/*"))


def _import_context_skip_reason(
    stripped: str,
    file_text: str | None,
    line_number: int | None,
) -> ExtractionSkipReason | None:
    if file_text is None or line_number is None:
        return None
    if line_number not in _import_declaration_line_numbers(file_text):
        return None
    return _import_skip_reason(stripped) or ExtractionSkipReason.NON_DOMAIN_BOILERPLATE


# RA-17-003: table-driven structural skip rules — each (predicate, reason) is tried in order and the
# first match wins (same short-circuit semantics as the previous if-chains). Predicates are lambdas so
# helper functions defined later in the module resolve at call time.
_StructuralRule = tuple[Callable[[str], bool], ExtractionSkipReason]


def _first_matching_reason(stripped: str, rules: tuple[_StructuralRule, ...]) -> ExtractionSkipReason | None:
    for predicate, reason in rules:
        if predicate(stripped):
            return reason
    return None


_TYPE_OR_MOCK_RULES: tuple[_StructuralRule, ...] = (
    (lambda s: TYPE_DECLARATION_PATTERN.match(s) is not None, ExtractionSkipReason.TYPE_DECLARATION),
    (lambda s: MOCK_SETUP_PATTERN.search(s) is not None, ExtractionSkipReason.MOCK_SETUP),
    (lambda s: LIFECYCLE_HOOK_PATTERN.match(s) is not None, ExtractionSkipReason.TEST_FRAMEWORK_SCAFFOLD),
)

# Signatures/plumbing are never claims, even when names mention domain words.
_PLUMBING_RULES: tuple[_StructuralRule, ...] = (
    (lambda s: _is_non_test_function_signature(s), ExtractionSkipReason.FUNCTION_SIGNATURE),
    (lambda s: TYPE_ALIAS_PATTERN.match(s) is not None, ExtractionSkipReason.TYPE_ALIAS),
    (lambda s: MESSAGE_CONSTANT_PATTERN.match(s) is not None, ExtractionSkipReason.IMPLEMENTATION_PLUMBING),
    (lambda s: ROUTER_PLUMBING_PATTERN.match(s) is not None, ExtractionSkipReason.IMPLEMENTATION_PLUMBING),
    (
        lambda s: PARAM_ANNOTATION_ONLY_PATTERN.match(s) is not None
        or PYDANTIC_CLASS_PATTERN.match(s) is not None,
        ExtractionSkipReason.TYPE_DECLARATION,
    ),
    (lambda s: _is_thin_module_doc_line(s), ExtractionSkipReason.IMPLEMENTATION_PLUMBING),
    (lambda s: _is_bare_test_mechanic_line(s), ExtractionSkipReason.TEST_FRAMEWORK_SCAFFOLD),
    (lambda s: _is_implementation_plumbing_line(s), ExtractionSkipReason.IMPLEMENTATION_PLUMBING),
)


def _structural_type_or_mock_skip(stripped: str) -> ExtractionSkipReason | None:
    return _first_matching_reason(stripped, _TYPE_OR_MOCK_RULES) or _import_skip_reason(stripped)


def _structural_plumbing_skip(stripped: str) -> ExtractionSkipReason | None:
    return _first_matching_reason(stripped, _PLUMBING_RULES)


def _classify_structural_skip_reason(stripped: str) -> ExtractionSkipReason | None:
    type_reason = _structural_type_or_mock_skip(stripped)
    if type_reason is not None:
        return type_reason

    plumbing_reason = _structural_plumbing_skip(stripped)
    if plumbing_reason is not None:
        return plumbing_reason

    frontend_reason = _classify_frontend_plumbing_skip(stripped)
    if frontend_reason is not None:
        return frontend_reason
    if PACKAGE_MARKER_PATH_PATTERN.search(stripped.replace("\\", "/")):
        return ExtractionSkipReason.PACKAGE_MARKER_PATH
    # Health/platform smoke before domain-keyword early-outs ("scenario", "status", etc.).
    if _is_health_or_platform_smoke_line(stripped):
        return ExtractionSkipReason.HEALTH_OR_PLATFORM_SMOKE
    return None


def _scaffold_smoke_skip(stripped: str) -> ExtractionSkipReason | None:
    # Presence assertions are UI smoke/scaffold even when testids mention domain words.
    if GENERIC_EXPECT_PATTERN.search(stripped):
        return ExtractionSkipReason.GENERIC_RENDER_TEST
    if SELECTOR_PATTERN.search(stripped) and not has_strong_product_behavior_signal(stripped):
        return ExtractionSkipReason.STYLING_OR_SELECTOR
    if _is_generic_smoke_test_line(stripped):
        if _is_health_or_platform_smoke_line(stripped):
            return ExtractionSkipReason.HEALTH_OR_PLATFORM_SMOKE
        return ExtractionSkipReason.GENERIC_SMOKE_TEST
    if _is_health_or_platform_smoke_line(stripped):
        return ExtractionSkipReason.HEALTH_OR_PLATFORM_SMOKE
    return None


def _scaffold_render_skip(stripped: str) -> ExtractionSkipReason | None:
    technical_reason = classify_test_skip_reason(stripped)
    if technical_reason is not None:
        return technical_reason

    js_test = JS_TEST_NAME_PATTERN.search(stripped)
    if js_test is not None and _is_generic_test_title(js_test.group(1)):
        if not has_strong_product_behavior_signal(stripped):
            return ExtractionSkipReason.GENERIC_RENDER_TEST
    if GENERIC_RENDER_PATTERN.match(stripped):
        return ExtractionSkipReason.GENERIC_RENDER_TEST
    if RENDER_CALL_PATTERN.search(stripped) and not has_strong_product_behavior_signal(stripped):
        return ExtractionSkipReason.GENERIC_RENDER_TEST
    if _is_generic_bdd_setup_step(stripped):
        return ExtractionSkipReason.TEST_FRAMEWORK_SCAFFOLD
    if _is_generic_status_snippet(stripped):
        return ExtractionSkipReason.NON_DOMAIN_BOILERPLATE
    if BASE_URL_LITERAL_PATTERN.match(stripped):
        return ExtractionSkipReason.NON_DOMAIN_BOILERPLATE
    if stripped.lower().startswith("describe("):
        return ExtractionSkipReason.TEST_FRAMEWORK_SCAFFOLD
    return None


def _classify_scaffold_test_skip_reason(stripped: str) -> ExtractionSkipReason | None:
    smoke_reason = _scaffold_smoke_skip(stripped)
    if smoke_reason is not None:
        return smoke_reason
    return _scaffold_render_skip(stripped)


def classify_line_skip_reason(
    line: str,
    *,
    file_text: str | None = None,
    line_number: int | None = None,
) -> ExtractionSkipReason | None:
    stripped = line.strip()
    if _is_comment_or_blank_line(stripped):
        return None

    import_context_reason = _import_context_skip_reason(stripped, file_text, line_number)
    if import_context_reason is not None:
        return import_context_reason

    structural_reason = _classify_structural_skip_reason(stripped)
    if structural_reason is not None:
        return structural_reason

    if is_domain_symbol_usage_line(stripped):
        return None

    return _classify_scaffold_test_skip_reason(stripped)


def _frontend_hook_or_query_skip(stripped: str, lowered: str, compact: str) -> ExtractionSkipReason | None:
    if HOOK_ARROW_PATTERN.match(stripped):
        return ExtractionSkipReason.HOOK_OR_QUERY_HELPER_TEST
    if any(marker in compact or marker in lowered for marker in HOOK_OR_QUERY_HELPER_MARKERS):
        if not has_strong_product_behavior_signal(stripped):
            return ExtractionSkipReason.HOOK_OR_QUERY_HELPER_TEST
    return None


def _frontend_grid_or_datasource_skip(stripped: str, lowered: str, compact: str) -> ExtractionSkipReason | None:
    if any(marker in lowered for marker in GRID_CALLBACK_MARKERS):
        if not has_strong_product_behavior_signal(stripped):
            return ExtractionSkipReason.FRONTEND_TEST_PLUMBING
    if "datasource" in lowered or "createdatasource" in compact:
        # Return-value / factory plumbing (companyId missing is not product deny language).
        if not _has_strong_authz_visibility(stripped):
            return ExtractionSkipReason.DATASOURCE_FACTORY_TEST
    return None


def _classify_frontend_plumbing_skip(line: str) -> ExtractionSkipReason | None:
    """Skip JSX/render/hook/grid/datasource plumbing unless strong product behavior."""
    stripped = line.strip()
    lowered = stripped.lower()

    if JSX_ONLY_PATTERN.match(stripped):
        return ExtractionSkipReason.JSX_RENDER_ONLY

    if RENDER_HELPER_PATTERN.search(stripped):
        if not has_strong_product_behavior_signal(stripped):
            return ExtractionSkipReason.FRONTEND_TEST_PLUMBING

    compact = re.sub(r"[\s_'\"`()<>]", "", lowered)
    hook_reason = _frontend_hook_or_query_skip(stripped, lowered, compact)
    if hook_reason is not None:
        return hook_reason

    grid_reason = _frontend_grid_or_datasource_skip(stripped, lowered, compact)
    if grid_reason is not None:
        return grid_reason

    if RETURNS_NULL_UNDEFINED_PATTERN.search(stripped) and not _has_strong_authz_visibility(stripped):
        # "returns null when unauthenticated" is hook/router plumbing, not a product rule.
        return ExtractionSkipReason.HOOK_OR_QUERY_HELPER_TEST

    return None


def has_strong_product_behavior_signal(text: str) -> bool:
    """True for product behavior wording, not mere domain-ish component names."""
    return _has_strong_authz_visibility(text) or _text_has_strong_product_keyword(text)


def _has_strong_authz_visibility(text: str) -> bool:
    lowered = text.lower().replace("_", " ")
    authz_markers = (
        "permission",
        "authorize",
        "authorization",
        "authorized",
        "unauthorized",
        "deny",
        "denied",
        "forbidden",
        _CONTRACT_MUST_NOT,
        "cannot",
        _CONTRACT_CANT,
        "not allowed",
        "role",
        "visibility",
        "visible to",
        "hidden from",
    )
    return any(marker in lowered for marker in authz_markers)


def _is_component_name_keyword_match(keyword: str, lowered: str) -> bool:
    """True when keyword matches but only as a component/identifier suffix (Tab/Page/View)."""
    component_suffixes = ("tab", "page", "view")
    for suffix in component_suffixes:
        if re.search(rf"(?<![a-z0-9]){re.escape(keyword)}[a-z]*{suffix}\b", lowered):
            return True
    return False


def _text_has_strong_product_keyword(text: str) -> bool:
    lowered = text.lower().replace("_", " ")
    # Avoid treating PascalCase component names as behavior (AssignmentsTab).
    if JSX_ONLY_PATTERN.match(text.strip()) or RENDER_HELPER_PATTERN.search(text):
        return _has_strong_authz_visibility(text)
    for keyword in STRONG_PRODUCT_BEHAVIOR_KEYWORDS:
        if " " in keyword:
            if keyword in lowered:
                return True
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(keyword)}", lowered):
            if _is_component_name_keyword_match(keyword, lowered):
                continue
            return True
    return False


def _is_health_or_platform_smoke_line(line: str) -> bool:
    lowered = line.lower().replace("_", " ")
    if any(marker in lowered for marker in HEALTH_PLATFORM_BDD_MARKERS):
        # Keep only explicit SLA/compliance product policy wording.
        compliance = ("sla", "compliance", "uptime policy", "availability policy", "retention")
        return not any(token in lowered for token in compliance)
    return False


def is_package_marker_path(path: str | None) -> bool:
    if not path:
        return False
    return bool(PACKAGE_MARKER_PATH_PATTERN.search(path.replace("\\", "/")))


def _is_generic_bdd_setup_step(line: str) -> bool:
    match = match_bdd_step(line)
    if match is None:
        return False
    step_body = match.strip().lower().rstrip(".:")
    return bool(any(step_body == phrase or step_body.startswith(phrase) for phrase in GENERIC_BDD_SETUP_STEPS))


def _is_generic_smoke_test_line(line: str) -> bool:
    name = _extract_test_name(line)
    if name is not None and _is_generic_smoke_test_name(name.lower()):
        return True
    return bool(STATUS_OK_LITERAL_PATTERN.match(line))


def _is_generic_smoke_test_name(name_lower: str) -> bool:
    spaced = name_lower.replace("_", " ")
    if any(phrase in spaced or phrase in name_lower for phrase in GENERIC_SMOKE_TEST_TITLES):
        return True
    smoke_hints = (
        "importable",
        "health_endpoint",
        "healthcheck",
        "smoke",
        "returns_ok",
        "returns_200",
        "readiness",
        "liveness",
        "module_imports",
        "module_import",
        "platform_system",
        "system_check",
        "platform_health",
    )
    return any(hint in name_lower for hint in smoke_hints)


def _extract_test_name(line_or_name: str) -> str | None:
    stripped = line_or_name.strip()
    python_match = PYTHON_TEST_DEF_PATTERN.search(stripped)
    if python_match is not None:
        return python_match.group(1)
    js_match = JS_TEST_NAME_PATTERN.search(stripped)
    if js_match is not None:
        return js_match.group(1)
    if stripped.startswith(("test_", "it(", "test(")):
        return stripped
    if re.fullmatch(r"test_[\w]+", stripped):
        return stripped
    return None


def _is_generic_status_snippet(line: str) -> bool:
    """Bare ``status_code = 400`` / ``statusCode: 201`` lines carry no domain context.

    We only check the literal-only pattern here; the check happens after
    behavioural context checks in ``classify_line_skip_reason`` so anything
    with permission/role words never reaches this branch.
    """
    return bool(STATUS_CODE_ONLY_PATTERN.match(line))


def is_non_business_rule_scaffold_line(
    line: str,
    *,
    file_text: str | None = None,
    line_number: int | None = None,
) -> bool:
    return classify_line_skip_reason(line, file_text=file_text, line_number=line_number) is not None


def is_domain_symbol_usage_line(line: str) -> bool:
    """Imported domain constants/enums may support evidence on behavioral usage lines."""
    stripped = line.strip()
    if not stripped or is_import_declaration_line(stripped):
        return False
    if not (UPPER_DOMAIN_CONSTANT_PATTERN.search(stripped) or ENUM_MEMBER_PATTERN.search(stripped)):
        return False
    if DOMAIN_SYMBOL_USAGE_PATTERN.search(stripped):
        return True
    return bool(is_potential_business_behavior_line(stripped))


def is_import_declaration_line(line: str) -> bool:
    return _import_skip_reason(line.strip()) is not None


def is_potential_business_behavior_line(line: str) -> bool:
    if has_domain_behavior_signal(line):
        return True
    step_text = match_bdd_step(line.strip())
    if step_text is not None and has_domain_behavior_signal(step_text):
        return True
    js_test = JS_TEST_NAME_PATTERN.search(line)
    if js_test is not None and has_domain_behavior_signal(js_test.group(1)):
        return True
    python_test = PYTHON_TEST_DEF_PATTERN.search(line)
    return bool(python_test is not None and has_domain_behavior_signal(python_test.group(1)))


def has_domain_behavior_signal(text: str, *, path: str | None = None) -> bool:
    """True when text (and optional path) contain meaningful product/domain concepts."""
    if _text_has_domain_keyword(text):
        return True
    if STATUS_CODE_PATTERN.search(text):
        return True
    return bool(path and _text_has_domain_keyword(path.replace("/", " ").replace("-", " ").replace(".", " ")))


def _text_has_domain_keyword(text: str) -> bool:
    """Match domain keywords at token starts.

    Leading-boundary matching allows stems like ``expir``/``assign``/``attempt`` to
    hit ``expired``/``assignments``/``attempts``, while avoiding mid-token hits.
    Multi-word phrases still use substring match.
    """
    lowered = text.lower().replace("_", " ")
    for keyword in DOMAIN_BEHAVIOR_KEYWORDS:
        if " " in keyword:
            if keyword in lowered:
                return True
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(keyword)}", lowered):
            return True
    return False


def _classify_test_skip_from_name(name: str, line_or_name: str) -> ExtractionSkipReason | None:
    name_lower = name.lower()
    if _is_health_or_platform_smoke_line(name):
        return ExtractionSkipReason.HEALTH_OR_PLATFORM_SMOKE
    if _is_generic_smoke_test_name(name_lower):
        return ExtractionSkipReason.GENERIC_SMOKE_TEST
    if any(marker in name_lower for marker in TECHNICAL_HELPER_TEST_NAME_MARKERS):
        return ExtractionSkipReason.TECHNICAL_HELPER_TEST
    if any(marker in name_lower for marker in GRID_CALLBACK_MARKERS):
        if not has_strong_product_behavior_signal(name):
            return ExtractionSkipReason.FRONTEND_TEST_PLUMBING
    if RETURNS_NULL_UNDEFINED_PATTERN.search(name) and not _has_strong_authz_visibility(name):
        return ExtractionSkipReason.HOOK_OR_QUERY_HELPER_TEST
    if "datasource" in name_lower and not _has_strong_authz_visibility(name):
        return ExtractionSkipReason.DATASOURCE_FACTORY_TEST
    return _classify_frontend_plumbing_skip(line_or_name)


def _classify_test_skip_from_path(path: str, combined: str) -> ExtractionSkipReason | None:
    path_lower = path.lower().replace("\\", "/")
    if is_package_marker_path(path_lower):
        return ExtractionSkipReason.PACKAGE_MARKER_PATH
    if any(marker in path_lower for marker in TECHNICAL_HELPER_PATH_MARKERS):
        if not has_domain_behavior_signal(combined, path=path):
            return ExtractionSkipReason.UTILITY_FUNCTION_TEST
    return None


def _classify_test_skip_from_body(
    line_or_name: str,
    body: str,
    combined: str,
    *,
    path: str | None,
) -> ExtractionSkipReason | None:
    strong = has_strong_product_behavior_signal(combined)
    if not strong and not has_domain_behavior_signal(combined, path=path):
        if PYTHON_TEST_DEF_PATTERN.search(line_or_name) or JS_TEST_NAME_PATTERN.search(line_or_name):
            return ExtractionSkipReason.NON_DOMAIN_UNIT_TEST
    if _classify_frontend_plumbing_skip(body) is not None and not strong:
        return ExtractionSkipReason.FRONTEND_TEST_PLUMBING
    if strong:
        return None
    if RENDER_HELPER_PATTERN.search(combined) or RENDER_CALL_PATTERN.search(combined):
        return ExtractionSkipReason.FRONTEND_TEST_PLUMBING
    if JSX_ONLY_PATTERN.search(body) or ("<" in body and "/>" in body):
        return ExtractionSkipReason.JSX_RENDER_ONLY
    return None


def classify_test_skip_reason(
    line_or_name: str,
    *,
    body: str | None = None,
    path: str | None = None,
) -> ExtractionSkipReason | None:
    """Classify a unit-test name/line as a non-business technical/helper/smoke test.

    Clear technical-helper and smoke names are skipped from the name alone.
    Broader non-domain rejection requires body context so domain-bodied tests
    whose names lack keywords are not dropped prematurely.
    """
    name = _extract_test_name(line_or_name)
    if name is None:
        return None

    name_reason = _classify_test_skip_from_name(name, line_or_name)
    if name_reason is not None:
        return name_reason

    combined = f"{name}\n{body or ''}"
    if path:
        path_reason = _classify_test_skip_from_path(path, combined)
        if path_reason is not None:
            return path_reason

    if body is not None:
        return _classify_test_skip_from_body(line_or_name, body, combined, path=path)
    return None


def find_domain_test_blocks(text: str, *, path: str | None = None) -> list[tuple[int, int, str]]:
    """Return (start_line, end_line, claim_text) for domain-bearing unit tests only.

    Evidence ranges start at the test function/title and end at the last relevant
    assertion, never at surrounding import lines.
    """
    blocks = _python_domain_test_blocks(text, path=path)
    if blocks:
        return blocks
    return _js_domain_test_blocks(text, path=path)


def is_scaffold_evidence_text(claim_text: str, snippet: str | None = None) -> bool:
    for block in (claim_text, snippet or ""):
        if _is_implementation_plumbing_line(block):
            return True
        for line_number, line in enumerate(block.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            if is_non_business_rule_scaffold_line(stripped, file_text=block, line_number=line_number):
                return True
    return False


def _is_non_test_function_signature(line: str) -> bool:
    """True for implementation function headers, not unit-test definitions."""
    stripped = line.strip()
    if not FUNCTION_SIGNATURE_PATTERN.match(stripped):
        return False
    if PYTHON_TEST_DEF_PATTERN.search(stripped):
        return False
    return not (JS_IT_TEST_PATTERN.match(stripped) or JS_TEST_NAME_PATTERN.search(stripped))


def _is_implementation_plumbing_line(line: str) -> bool:
    lowered = line.lower()
    if any(phrase in lowered for phrase in IMPLEMENTATION_PLUMBING_PHRASES):
        return True
    # Bare function/class headers or dependency aliases are not product rules.
    if _is_non_test_function_signature(line) or TYPE_ALIAS_PATTERN.match(line.strip()):
        return True
    if MESSAGE_CONSTANT_PATTERN.match(line.strip()):
        return True
    if ROUTER_PLUMBING_PATTERN.match(line.strip()):
        return True
    if _is_thin_module_doc_line(line):
        return True
    # detail={"detail": MSG_...} style error wiring
    return bool(re.search("detail\\s*=\\s*\\{[\\\"']detail[\\\"']\\s*:", line) and "MSG_" in line)


def _is_thin_module_doc_line(line: str) -> bool:
    """One-line module blurbs and route-helper prose without product behavior."""
    stripped = line.strip().strip("\"'`")
    if not stripped:
        return False
    lowered = stripped.lower()
    if any(marker in lowered for marker in THIN_MODULE_DOC_MARKERS):
        return True
    # Short "Admin X (native …)" / "Admin X list (``/api/...``)" module titles.
    if re.match(r"^(admin|staff|workspace)\b.+\([^)]{0,80}\)\.?$", lowered):
        if not has_strong_product_behavior_signal(stripped):
            return True
    return False


def _is_bare_test_mechanic_line(line: str) -> bool:
    """Bare asserts and monkeypatch setup without product-behavior wording."""
    stripped = line.strip()
    if MONKEYPATCH_PATTERN.search(stripped):
        return True
    if not BARE_ASSERT_PATTERN.match(stripped):
        return False
    return not has_strong_product_behavior_signal(stripped)


def find_test_evidence_lines(text: str, *, path: str | None = None) -> list[tuple[int, str]]:
    """Return line numbers and text for domain-bearing test evidence, skipping scaffold."""
    blocks = find_domain_test_blocks(text, path=path)
    if blocks:
        return [(start, claim) for start, _end, claim in blocks]

    results: list[tuple[int, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if is_non_business_rule_scaffold_line(stripped, file_text=text, line_number=line_number):
            continue
        if classify_test_skip_reason(stripped, path=path) is not None:
            continue
        if not _line_looks_like_test_evidence(stripped):
            continue
        if not is_potential_business_behavior_line(stripped) and not _line_has_domain_assertion(stripped):
            continue
        results.append((line_number, stripped))
    return results


def _matches_non_domain_import_pattern(line: str) -> bool:
    return bool(
        IMPORT_LINE_PATTERN.match(line)
        or PYTHON_IMPORT_PATTERN.match(line)
        or JAVA_KOTLIN_IMPORT_PATTERN.match(line)
        or CSHARP_USING_PATTERN.match(line)
        or GO_IMPORT_PATTERN.match(line)
        or GO_IMPORT_STRING_PATTERN.match(line)
        or RUBY_REQUIRE_PATTERN.match(line)
        or PHP_USE_PATTERN.match(line)
    )


def _import_skip_reason(line: str) -> ExtractionSkipReason | None:
    if not line:
        return None
    if _is_framework_import_line(line):
        return ExtractionSkipReason.FRAMEWORK_IMPORT
    if line.lower().startswith("export ") and not _export_has_domain_signal(line):
        return ExtractionSkipReason.NON_DOMAIN_BOILERPLATE
    if _matches_non_domain_import_pattern(line):
        return ExtractionSkipReason.NON_DOMAIN_BOILERPLATE
    return None


def _extend_blocked_multiline_import(lines: list[str], index: int, blocked: set[int], *, close_marker: str) -> int:
    end_index = index
    while end_index < len(lines) and close_marker not in lines[end_index]:
        end_index += 1
    blocked.update(range(index + 1, min(end_index + 2, len(lines) + 1)))
    return end_index + 1


def _import_declaration_line_numbers(text: str) -> set[int]:
    lines = text.splitlines()
    blocked: set[int] = set()
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if GO_IMPORT_PATTERN.match(stripped) and stripped.endswith("("):
            end_index = index
            while end_index < len(lines) and not lines[end_index].strip().endswith(")"):
                end_index += 1
            blocked.update(line_no for line_no in range(index + 1, end_index + 2) if line_no <= len(lines))
            index = end_index + 1
            continue

        if IMPORT_LINE_PATTERN.match(stripped) and "{" in stripped and "}" not in stripped:
            index = _extend_blocked_multiline_import(lines, index, blocked, close_marker="}")
            continue

        if _import_skip_reason(stripped) is not None:
            blocked.add(index + 1)
        index += 1
    return blocked


def _is_framework_import_line(line: str) -> bool:
    lowered = line.lower()
    if any(marker in lowered for marker in FRAMEWORK_MODULE_MARKERS):
        return True
    if not IMPORT_LINE_PATTERN.match(line):
        return False
    if re.search(r"""import\s+['"][^'"]+['"]""", line):
        # JS/TS side-effect import or Go single import — still framework/scaffold, not a rule.
        return "from" not in lowered
    if "from" not in lowered and re.search(r"\bimport\s+[A-Z]\w*", line):
        # Default import of a PascalCase module (e.g. import React).
        return True
    return False


def _export_has_domain_signal(line: str) -> bool:
    lowered = line.lower()
    return any(keyword in lowered for keyword in DOMAIN_BEHAVIOR_KEYWORDS)


def _is_generic_test_title(title: str) -> bool:
    lowered = title.strip().lower()
    if any(phrase in lowered for phrase in GENERIC_RENDER_PHRASES):
        return True
    if lowered in {"renders", "render", "mounts", "works", "smoke test"}:
        return True
    if lowered.startswith("component"):
        return True
    return bool(
        re.match(r"^[A-Z]\w+$", title.strip())
        and not any(keyword in lowered for keyword in DOMAIN_BEHAVIOR_KEYWORDS)
    )


def _line_looks_like_test_evidence(line: str) -> bool:
    if match_bdd_step(line) is not None:
        return True
    if PYTHON_TEST_DEF_PATTERN.search(line):
        return True
    if JS_IT_TEST_PATTERN.match(line):
        return True
    return bool(ASSERT_EXPECT_PATTERN.search(line))


def _line_has_domain_assertion(line: str) -> bool:
    if is_potential_business_behavior_line(line):
        return True
    return bool(
        re.search("expect\\([^)]+\\)\\.(toBe|toEqual|toStrictEqual)\\(", line) and STATUS_CODE_PATTERN.search(line)
    )


def _select_domain_test_claim(
    name: str,
    body_lines: list[str],
    *,
    signal_fn: Callable[[str], bool],
    assertion_fn: Callable[[str], bool],
) -> str:
    claim = name
    for body_line in body_lines:
        if signal_fn(body_line) or assertion_fn(body_line):
            claim = body_line
            break
    if signal_fn(name):
        claim = name
    return claim


def _collect_python_test_body(
    lines: list[str],
    *,
    start_line: int,
    indent: int,
) -> tuple[list[str], int]:
    body_lines: list[str] = []
    assertion_end = start_line
    for line_number in range(start_line + 1, len(lines) + 1):
        raw = lines[line_number - 1]
        if not raw.strip():
            continue
        leading = len(raw) - len(raw.lstrip(" \t"))
        if leading <= indent and not raw.lstrip().startswith("#"):
            break
        body_lines.append(raw.strip())
        if ASSERT_EXPECT_PATTERN.search(raw) or is_potential_business_behavior_line(raw):
            assertion_end = line_number
    return body_lines, assertion_end


def _python_domain_test_blocks(text: str, *, path: str | None = None) -> list[tuple[int, int, str]]:
    lines = text.splitlines()
    blocks: list[tuple[int, int, str]] = []
    for match in PYTHON_TEST_BLOCK_PATTERN.finditer(text):
        name = match.group(2)
        start_line = text.count("\n", 0, match.start()) + 1
        indent = len(match.group(1))
        body_lines, assertion_end = _collect_python_test_body(lines, start_line=start_line, indent=indent)
        body = "\n".join(body_lines)
        skip_reason = classify_test_skip_reason(
            f"def {name}():",
            body=body,
            path=path,
        )
        if skip_reason is not None:
            continue
        if not has_domain_behavior_signal(f"{name}\n{body}", path=path):
            continue

        claim = _select_domain_test_claim(
            name,
            body_lines,
            signal_fn=is_potential_business_behavior_line,
            assertion_fn=_line_has_domain_assertion,
        )
        blocks.append((start_line, max(assertion_end, start_line), claim))
    return blocks


def _collect_js_test_body(lines: list[str], *, line_number: int) -> tuple[list[str], int]:
    body_lines: list[str] = []
    assertion_end = line_number
    for follow_number in range(line_number + 1, len(lines) + 1):
        follow = lines[follow_number - 1]
        stripped = follow.strip()
        if not stripped:
            continue
        if re.match(r"^\s*(it|test|describe)\s*\(", follow):
            break
        if stripped in {"});", "}"}:
            break
        body_lines.append(stripped)
        if ASSERT_EXPECT_PATTERN.search(follow) or has_strong_product_behavior_signal(follow):
            assertion_end = follow_number
    return body_lines, assertion_end


def _js_domain_test_blocks(text: str, *, path: str | None = None) -> list[tuple[int, int, str]]:
    lines = text.splitlines()
    blocks: list[tuple[int, int, str]] = []
    for line_number, line in enumerate(lines, start=1):
        match = JS_TEST_NAME_PATTERN.search(line)
        if match is None:
            continue
        if not re.match(r"^\s*(it|test)\s*\(", line):
            continue
        title = match.group(1)
        body_lines, assertion_end = _collect_js_test_body(lines, line_number=line_number)
        body = "\n".join(body_lines)
        skip_reason = classify_test_skip_reason(line, body=body, path=path)
        if skip_reason is not None:
            continue
        combined = f"{title}\n{body}"
        # Frontend tests need strong product behavior, not domain-ish component names.
        if not has_strong_product_behavior_signal(combined):
            continue
        if is_scaffold_evidence_text(title) or is_scaffold_evidence_text(body):
            continue

        claim = _select_domain_test_claim(
            title,
            body_lines,
            signal_fn=has_strong_product_behavior_signal,
            assertion_fn=_line_has_domain_assertion,
        )
        if is_non_business_rule_scaffold_line(claim):
            continue
        blocks.append((line_number, max(assertion_end, line_number), claim))
    return blocks
