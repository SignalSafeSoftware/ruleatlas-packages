from __future__ import annotations

import re

_CONTRACT_CANT = "can't"
_CONTRACT_MUST_NOT = "must not"

FRAMEWORK_MODULE_MARKERS = (
    "vitest",
    "jest",
    "@testing-library/",
    "@playwright/test",
    "@vue/test-utils",
    "react",
    "react-dom",
    "react/",
    "pytest",
    "unittest",
    "mocha",
    "chai",
    "sinon",
    "enzyme",
    "@jest/",
    "testing-library",
)

DOMAIN_BEHAVIOR_KEYWORDS = (
    "permission",
    "authorization",
    "authorize",
    "forbid",
    "forbidden",
    "deny",
    "denied",
    "prevent",
    "cannot",
    _CONTRACT_CANT,
    _CONTRACT_MUST_NOT,
    "mustn't",
    "retention",
    "retain",
    "expir",
    "purge",
    "deletes",
    "deleted",
    "deleting",
    "deletion",
    "eligible",
    "ineligible",
    "assign",
    "assignment",
    "attempt",
    "decision",
    "scenario",
    "lesson",
    "campaign",
    "course",
    "enroll",
    "tenant",
    "company",
    "staff",
    "user access",
    "status",
    "transition",
    "outcome",
    "workflow",
    "validation",
    "validate",
    "reject",
    "rejection",
    "unauthorized",
    "forbidden",
    "pricing",
    "price",
    "billing",
    "payment",
    "security",
    "compliance",
    "reporting",
    "report",
    "quota",
    "limit",
    "policy",
    "role",
    "admin",
    "manager",
    "company access",
    "without access",
    "less than",
    "greater than",
    "before",
    "after",
    "minimum",
    "maximum",
    "due date",
    "due_date",
    "blocks submission",
    "workspace",
)

TECHNICAL_HELPER_TEST_NAME_MARKERS = (
    "row_str",
    "row_int",
    "row_opt",
    "row_float",
    "row_bool",
    "value_helper",
    "formatting",
    "format_",
    "_format",
    "uuid_",
    "_uuid",
    "test_env_",
    "env_var",
    "env_parse",
    "importable",
    "module_imports",
    "module_import",
    "handles_none",
    "default_and_coercion",
    "coercion",
    "serialize",
    "serializer",
    "deserialize",
    "parse_int",
    "parse_str",
    "parse_float",
    "to_str",
    "to_int",
    "to_float",
    "stringify",
    "stringif",
    "type_coercion",
    "none_default",
    "default_value",
    "helper_function",
    "utility_function",
)

TECHNICAL_HELPER_PATH_MARKERS = (
    "value_helpers",
    "test_value_helpers",
    "/helpers/",
    "helpers/test_",
    "test_helpers",
    "utils/test_",
    "test_utils",
    "test_formatting",
    "test_serializers",
    "test_parsing",
)

GENERIC_RENDER_PHRASES = (
    "renders without crashing",
    "renders correctly",
    "should render",
    "renders ",
    "render component",
    "snapshot",
)

GENERIC_BDD_SETUP_STEPS = (
    "the api base url is configured",
    "the api client is ready",
    "the staff client is ready",
    "the client is ready",
    "the admin client is ready",
    "the user is authenticated",
    "the auth token is set",
    "the auth fixture is configured",
    "the database is seeded",
    "the test database is prepared",
    "the app is running",
    "the server is running",
    "a session is started",
    "the environment is configured",
    "test data is loaded",
)

GENERIC_SMOKE_TEST_TITLES = (
    "app is importable",
    "module is importable",
    "package is importable",
    "health endpoint returns ok",
    "health endpoint returns 200",
    "healthcheck returns ok",
    "readiness endpoint returns ok",
    "liveness endpoint returns ok",
    "returns ok",
    "smoke test",
    "platform system check",
    "system check returns ok",
    "system check",
    "health endpoint",
    "platform health",
)

# Product-behavior wording required to keep frontend/render/hook plumbing claims.
STRONG_PRODUCT_BEHAVIOR_KEYWORDS = (
    "permission",
    "authorize",
    "authorization",
    "authorized",
    "unauthorized",
    "deny",
    "denied",
    "forbidden",
    "role",
    "company",
    "tenant",
    "workspace",
    "visibility",
    "visible",
    "hidden",
    _CONTRACT_MUST_NOT,
    "cannot",
    _CONTRACT_CANT,
    "must ",
    "retention",
    "expir",
    "delet",
    "approv",
    "transition",
    "assignment",
    "attempt",
    "decision",
    "campaign",
    "lesson",
    "course",
    "scenario",
    "staff",
    "admin",
    "manager",
    "owner",
)

_BDD_STEP_KEYWORDS = ("Given", "When", "Then", "And")


def match_bdd_step(line: str) -> str | None:
    """Return the BDD step body if *line* is a Given/When/Then/And step.

    Implemented without regex so matching stays linear (Sonar S8786).
    """
    i = 0
    length = len(line)
    while i < length and line[i] in " \t":
        i += 1
    for keyword in _BDD_STEP_KEYWORDS:
        end = i + len(keyword)
        if end > length or line[i:end].casefold() != keyword.casefold():
            continue
        if end >= length or line[end] not in " \t":
            return None
        j = end
        while j < length and line[j] in " \t":
            j += 1
        body = line[j:].rstrip("\r\n")
        return body if body else None
    return None
PYTHON_TEST_DEF_PATTERN = re.compile(r"^\s*def\s+(test_[\w]+)", re.IGNORECASE)
JS_IT_TEST_PATTERN = re.compile(r"^\s*(it|test)\s*\(\s*['\"]", re.IGNORECASE)
JS_TEST_NAME_PATTERN = re.compile(
    r"""(?:it|test|describe)\s*\(\s*['"]([^'"]+)['"]""",
    re.IGNORECASE,
)
IMPORT_LINE_PATTERN = re.compile(r"^\s*(import|export)\b", re.IGNORECASE)
PYTHON_IMPORT_PATTERN = re.compile(r"^\s*(import\s+\w|from\s+[\w.]+\s+import\s+)", re.IGNORECASE)
JAVA_KOTLIN_IMPORT_PATTERN = re.compile(r"^\s*(import\s+[\w.*]+;|package\s+[\w.]+;)\s*$")
CSHARP_USING_PATTERN = re.compile(r"^\s*using\s+(static\s+)?[\w.]+;\s*$", re.IGNORECASE)
GO_IMPORT_PATTERN = re.compile(r"^\s*import\s+(\(|\"[^\"]+\"|\w)", re.IGNORECASE)
GO_IMPORT_STRING_PATTERN = re.compile(r'^\s*"[^"]+"\s*$')
RUBY_REQUIRE_PATTERN = re.compile(r"^\s*(require|require_relative)\s+['\"]", re.IGNORECASE)
PHP_USE_PATTERN = re.compile(
    r"^\s*(?:use\s+[\w\\]+\s*;|require(?:_once)?\b|include(?:_once)?\b)",
    re.IGNORECASE,
)
DOMAIN_SYMBOL_USAGE_PATTERN = re.compile(
    r"\b(if|elif|unless|when|case|switch|raise|throw|return|assert|expect|validate|deny|reject|status)\b",
    re.IGNORECASE,
)
UPPER_DOMAIN_CONSTANT_PATTERN = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")
ENUM_MEMBER_PATTERN = re.compile(r"\b[A-Z]\w*\.[A-Z][A-Z0-9_]+\b")
TYPE_DECLARATION_PATTERN = re.compile(
    r"^\s*(export\s+)?(interface|type|enum)\s+\w+",
    re.IGNORECASE,
)
MOCK_SETUP_PATTERN = re.compile(
    r"^\s*(@patch|@mock\.patch|vi\.mock|jest\.mock|mock\.patch|unittest\.mock)",
    re.IGNORECASE,
)
LIFECYCLE_HOOK_PATTERN = re.compile(
    r"^\s*(beforeEach|afterEach|beforeAll|afterAll|setUp|tearDown)\s*\(",
    re.IGNORECASE,
)
GENERIC_RENDER_PATTERN = re.compile(
    r"^\s*(describe|it|test)\s*\(\s*['\"][^'\"]*("
    + "|".join(re.escape(p.strip()) for p in ("renders", "render", "snapshot", "mounts"))
    + r")",
    re.IGNORECASE,
)
RENDER_CALL_PATTERN = re.compile(r"\brender\s*\(\s*<", re.IGNORECASE)
GENERIC_EXPECT_PATTERN = re.compile(
    r"\.(toBeInTheDocument|toMatchSnapshot|toBeTruthy|toBeDefined|toBeNull)\s*\(",
    re.IGNORECASE,
)
SELECTOR_PATTERN = re.compile(
    r"(data-testid|getByTestId|getByRole|className\s*=|className:)",
    re.IGNORECASE,
)
STATUS_CODE_PATTERN = re.compile(r"\b(401|403|404|409|422|status)\b", re.IGNORECASE)
PYTHON_TEST_BLOCK_PATTERN = re.compile(
    r"^([ \t]*)def (test_\w+)\([^)\n]*\)[^\n]*:",
    re.MULTILINE,
)
ASSERT_EXPECT_PATTERN = re.compile(r"\b(assert|expect)\b", re.IGNORECASE)
_STATUS_CODE_ASSIGNMENT = r"(?:status_code|statusCode|status)\s*[:=]\s*\d{3}"
STATUS_CODE_ONLY_PATTERN = re.compile(
    rf"^\s*{_STATUS_CODE_ASSIGNMENT}\s*[,;]?\s*$",
    re.IGNORECASE,
)
STATUS_OK_LITERAL_PATTERN = re.compile(
    r"^\s*return\s*[{(]\s*[\"']status[\"']\s*[:=]\s*[\"']ok[\"']\s*[})]\s*$",
    re.IGNORECASE,
)
BASE_URL_LITERAL_PATTERN = re.compile(
    r"^\s*(?:api_base_url|base_url|api_url)\s*=\s*['\"][^'\"]+['\"]\s*$",
    re.IGNORECASE,
)
FUNCTION_SIGNATURE_PATTERN = re.compile(
    # Function/method headers (including multi-line signatures that open on this line).
    r"^\s*(?:"
    r"(?:async\s+)?def\s+\w+\s*\("
    r"|(?:export\s+)?(?:async\s+)?function\s+\w+\s*\("
    r"|(?:export\s+)?const\s+\w+\s*=\s*(?:async\s*)?\("
    r")",
    re.IGNORECASE,
)
TYPE_ALIAS_PATTERN = re.compile(
    r"^\s*(?:"
    r"\w+\s*=\s*Annotated\["
    r"|(?:export\s+)?type\s+\w+\s*="
    r"|(?:export\s+)?(?:const|let|var)\s+\w+Dep\s*="
    r"|\w+Dep\s*=\s*\w+"
    r")",
    re.IGNORECASE,
)
# Message/detail constants and router wiring are implementation plumbing, not product rules.
MESSAGE_CONSTANT_PATTERN = re.compile(
    r"^\s*(?:MSG_[A-Z0-9_]+|[A-Z][A-Z0-9_]+(?:_DETAIL|_MESSAGE|_ERROR|_MSG))\s*=\s*",
)
ROUTER_PLUMBING_PATTERN = re.compile(
    r"^\s*(?:"
    r"router\s*=\s*APIRouter\b"
    r"|[A-Z][A-Z0-9_]*_ROUTE_PREFIX\s*="
    r"|[A-Z][A-Z0-9_]*_PREFIX\s*=\s*['\"]/"
    r"|@router\.(?:get|post|put|patch|delete|api_route)\s*\("
    r")",
    re.IGNORECASE,
)
BARE_ASSERT_PATTERN = re.compile(r"^\s*assert\s+\S", re.IGNORECASE)
MONKEYPATCH_PATTERN = re.compile(r"\bmonkeypatch\.(setenv|setattr|delattr|undo)\b", re.IGNORECASE)
_PARAM_ANNOTATION_TYPES = r"(?:int|str|bool|float|UUID|dict|list|Any|Optional\[[^[\]]+\])"
PARAM_ANNOTATION_ONLY_PATTERN = re.compile(
    rf"^\s*\w+\s*:\s*{_PARAM_ANNOTATION_TYPES}\s*,?\s*$",
    re.IGNORECASE,
)
PYDANTIC_CLASS_PATTERN = re.compile(
    r"^\s*class\s+\w+(Response|Request|Schema|Model|Body|Params?)\s*\(",
    re.IGNORECASE,
)
THIN_MODULE_DOC_MARKERS = (
    "native phobos",
    "pydantic bodies for",
    "helpers for admin",
    "helpers for routes",
    "request bodies for",
    "drilldown filters shared",
)
IMPLEMENTATION_PLUMBING_PHRASES = (
    "fastapi dependencies",
    "typed aliases",
    "use these typed",
    "instead of repeating",
    "depends(get_",
    "composed fastapi",
    "repository kit",
    "production code must use",
    "must use phobos",
    "routers/health",
    "vitest.shared",
    "vitest.config",
    "extract_bearer_token",
    "authenticate_user(",
    "factory.get_repository",
    "as auditor",
    "workspace_test_force_auth",
)
# Self-closing JSX element on one line (match against stripped text).
JSX_ONLY_PATTERN = re.compile(r"^<[A-Z][\w.]*(?: [^/>]*)? ?/>;?$")
RENDER_HELPER_PATTERN = re.compile(
    r"\b(renderPage|renderRouter|renderAt|renderRoute)\s*\(",
    re.IGNORECASE,
)
HOOK_ARROW_PATTERN = re.compile(r"^\s*\(\s*\)\s*=>\s*use[A-Z]\w*")
HOOK_OR_QUERY_HELPER_MARKERS = (
    "usebulkselectedqueryparams",
    "queryparams",
    "usequery",
    "usemutation",
    "useselect",
    "usestate(",
    "useeffect(",
    "usememo(",
    "usecallback(",
)
GRID_CALLBACK_MARKERS = (
    "grid context callback",
    "through the grid",
    "coldef",
    "getrowid",
    "aggrid",
    "ag-grid",
    "rowmodel",
    "gridapi",
)
RETURNS_NULL_UNDEFINED_PATTERN = re.compile(
    r"\breturns\s+(null|undefined)\b|\btoBeNull\s*\(|\btoBeUndefined\s*\(",
    re.IGNORECASE,
)
PACKAGE_MARKER_PATH_PATTERN = re.compile(r"(^|/)__init__\.py$", re.IGNORECASE)
HEALTH_PLATFORM_BDD_MARKERS = (
    "platform system check",
    "system check",
    "health endpoint",
    "health check",
    "readiness",
    "liveness",
    "platform health",
    "docs endpoint",
    "ops api health",
    "returns html",
    "api health",
)


__all__ = [
    "ASSERT_EXPECT_PATTERN",
    "BARE_ASSERT_PATTERN",
    "BASE_URL_LITERAL_PATTERN",
    "CSHARP_USING_PATTERN",
    "DOMAIN_BEHAVIOR_KEYWORDS",
    "DOMAIN_SYMBOL_USAGE_PATTERN",
    "ENUM_MEMBER_PATTERN",
    "FRAMEWORK_MODULE_MARKERS",
    "FUNCTION_SIGNATURE_PATTERN",
    "GENERIC_BDD_SETUP_STEPS",
    "GENERIC_EXPECT_PATTERN",
    "GENERIC_RENDER_PATTERN",
    "GENERIC_RENDER_PHRASES",
    "GENERIC_SMOKE_TEST_TITLES",
    "GO_IMPORT_PATTERN",
    "GO_IMPORT_STRING_PATTERN",
    "GRID_CALLBACK_MARKERS",
    "HEALTH_PLATFORM_BDD_MARKERS",
    "HOOK_ARROW_PATTERN",
    "HOOK_OR_QUERY_HELPER_MARKERS",
    "IMPLEMENTATION_PLUMBING_PHRASES",
    "IMPORT_LINE_PATTERN",
    "JAVA_KOTLIN_IMPORT_PATTERN",
    "JSX_ONLY_PATTERN",
    "JS_IT_TEST_PATTERN",
    "JS_TEST_NAME_PATTERN",
    "LIFECYCLE_HOOK_PATTERN",
    "MESSAGE_CONSTANT_PATTERN",
    "MOCK_SETUP_PATTERN",
    "MONKEYPATCH_PATTERN",
    "PACKAGE_MARKER_PATH_PATTERN",
    "PARAM_ANNOTATION_ONLY_PATTERN",
    "PHP_USE_PATTERN",
    "PYDANTIC_CLASS_PATTERN",
    "PYTHON_IMPORT_PATTERN",
    "PYTHON_TEST_BLOCK_PATTERN",
    "PYTHON_TEST_DEF_PATTERN",
    "RENDER_CALL_PATTERN",
    "RENDER_HELPER_PATTERN",
    "RETURNS_NULL_UNDEFINED_PATTERN",
    "ROUTER_PLUMBING_PATTERN",
    "RUBY_REQUIRE_PATTERN",
    "SELECTOR_PATTERN",
    "STATUS_CODE_ONLY_PATTERN",
    "STATUS_CODE_PATTERN",
    "STATUS_OK_LITERAL_PATTERN",
    "STRONG_PRODUCT_BEHAVIOR_KEYWORDS",
    "TECHNICAL_HELPER_PATH_MARKERS",
    "TECHNICAL_HELPER_TEST_NAME_MARKERS",
    "THIN_MODULE_DOC_MARKERS",
    "TYPE_ALIAS_PATTERN",
    "TYPE_DECLARATION_PATTERN",
    "UPPER_DOMAIN_CONSTANT_PATTERN",
    "match_bdd_step",
]
