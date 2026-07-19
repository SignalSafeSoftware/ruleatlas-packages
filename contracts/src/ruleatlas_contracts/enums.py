from enum import StrEnum


class AnalysisVersionStatus(StrEnum):
    BUILDING = "building"
    READY = "ready"
    SUPERSEDED = "superseded"
    FAILED = "failed"


class ScanType(StrEnum):
    FULL = "full"
    DISCOVERY = "discovery"
    SELECTED_LOCATIONS = "selected_locations"
    CHANGED_FILES = "changed_files"
    DOCS_ONLY = "docs_only"
    TESTS_ONLY = "tests_only"
    RULE_RESCAN = "rule_rescan"
    DOMAIN_RESCAN = "domain_rescan"


class RuleCategory(StrEnum):
    BUSINESS = "business"
    SECURITY_AUTHORIZATION = "security_authorization"
    VALIDATION = "validation"
    WORKFLOW_LIFECYCLE = "workflow_lifecycle"
    CONFIGURATION = "configuration"
    ARCHITECTURE = "architecture"
    DEVELOPMENT_POLICY = "development_policy"
    TEST_COVERAGE = "test_coverage"
    RUNTIME_OBSERVATION = "runtime_observation"
    AI_GOVERNANCE = "ai_governance"
    UNKNOWN = "unknown"


class RuleRelationshipType(StrEnum):
    PARENT_OF = "parent_of"
    CHILD_OF = "child_of"
    DEPENDS_ON = "depends_on"
    TRIGGERS = "triggers"
    REQUIRES = "requires"
    CONSTRAINS = "constrains"
    OVERRIDES = "overrides"
    EXCEPTION_TO = "exception_to"
    SAME_AS = "same_as"
    CONFLICTS_WITH = "conflicts_with"
    IMPLEMENTED_BY = "implemented_by"
    TESTED_BY = "tested_by"
    DOCUMENTED_BY = "documented_by"


class RelationshipSuggestionStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ScanStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class AnalysisOutcomeStatus(StrEnum):
    """Truthful terminal/in-progress analysis outcome (distinct from ScanStatus lifecycle)."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    DEGRADED = "degraded"
    FAILED = "failed"
    CANCELED = "canceled"
    RESUMABLE = "resumable"


class ExtractionMethod(StrEnum):
    HEURISTIC = "heuristic"
    AI_SYNTHESIS = "ai_synthesis"
    COMPOSITE = "composite"


class AiSynthesisStatus(StrEnum):
    NOT_RUN = "not_run"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"


class DemoMode(StrEnum):
    """RuleAtlas demo-data mode. Offline never requires network or provider credentials."""

    OFFLINE = "offline"
    LIVE_AI = "live_ai"


class AuthMode(StrEnum):
    """API authentication enforcement mode."""

    DISABLED = "disabled"
    ENFORCED = "enforced"


class ScanStage(StrEnum):
    QUEUED = "queued"
    PREPARING_SOURCE = "preparing_source"
    INVENTORYING_FILES = "inventorying_files"
    CLASSIFYING_FILES = "classifying_files"
    STRUCTURAL_ANALYSIS = "structural_analysis"
    EXTRACTING_RULES = "extracting_rules"
    NORMALIZING_CLAIMS = "normalizing_claims"
    DETECTING_CONFLICTS = "detecting_conflicts"
    UPDATING_SEARCH_INDEX = "updating_search_index"
    COMPLETED = "completed"
    FAILED = "failed"


class ProjectEventType(StrEnum):
    SCAN_STARTED = "scan.started"
    SCAN_STAGE_CHANGED = "scan.stage_changed"
    SCAN_COMPLETED = "scan.completed"
    SCAN_FAILED = "scan.failed"
    SCAN_CANCELED = "scan.canceled"
    ANALYSIS_STAGE_PROGRESS = "analysis.stage_progress"
    ANALYSIS_PROVIDER_PROGRESS = "analysis.provider_progress"
    ANALYSIS_PIPELINE_COMPLETED = "analysis.pipeline_completed"


class SourceType(StrEnum):
    BACKEND_CODE = "backend_code"
    FRONTEND_CODE = "frontend_code"
    TESTS = "tests"
    BDD_SPECS = "bdd_specs"
    DOCS = "docs"
    DESIGN_DOCS = "design_docs"
    TICKETS = "tickets"
    COMMENTS = "comments"
    API_CONTRACT = "api_contract"
    SHARED_PACKAGE = "shared_package"
    EXTERNAL_PACKAGE = "external_package"
    UNKNOWN = "unknown"


class SourceLocationType(StrEnum):
    LOCAL_PATH = "local_path"
    GIT_REPO = "git_repo"
    URL = "url"
    ARCHIVE = "archive"
    UPLOADED_ZIP = "uploaded_zip"


class SourceTreeNodeKind(StrEnum):
    FOLDER = "folder"
    FILE = "file"


class SourceFileClassification(StrEnum):
    RULE_BEARING = "rule_bearing"
    UI_RULE_MIRROR = "ui_rule_mirror"
    TEST_EVIDENCE = "test_evidence"
    DOCUMENTATION_EVIDENCE = "documentation_evidence"
    TICKET_EVIDENCE = "ticket_evidence"
    DESIGN_DOC_EVIDENCE = "design_doc_evidence"
    COMMENT_EVIDENCE = "comment_evidence"
    PRESENTATION_ONLY = "presentation_only"
    OPS_ONLY = "ops_only"
    GENERATED_VENDOR = "generated_vendor"
    UNKNOWN_NEEDS_REVIEW = "unknown_needs_review"


class ExtractionSkipReason(StrEnum):
    FRAMEWORK_IMPORT = "framework_import"
    TEST_FRAMEWORK_SCAFFOLD = "test_framework_scaffold"
    MOCK_SETUP = "mock_setup"
    GENERIC_RENDER_TEST = "generic_render_test"
    JSX_RENDER_ONLY = "jsx_render_only"
    FRONTEND_TEST_PLUMBING = "frontend_test_plumbing"
    HOOK_OR_QUERY_HELPER_TEST = "hook_or_query_helper_test"
    DATASOURCE_FACTORY_TEST = "datasource_factory_test"
    PACKAGE_MARKER_PATH = "package_marker_path"
    HEALTH_OR_PLATFORM_SMOKE = "health_or_platform_smoke"
    TYPE_DECLARATION = "type_declaration"
    TYPE_ALIAS = "type_alias"
    FUNCTION_SIGNATURE = "function_signature"
    IMPLEMENTATION_PLUMBING = "implementation_plumbing"
    STYLING_OR_SELECTOR = "styling_or_selector"
    NON_DOMAIN_BOILERPLATE = "non_domain_boilerplate"
    NON_DOMAIN_UNIT_TEST = "non_domain_unit_test"
    TECHNICAL_HELPER_TEST = "technical_helper_test"
    UTILITY_FUNCTION_TEST = "utility_function_test"
    GENERIC_SMOKE_TEST = "generic_smoke_test"


class CommentClassification(StrEnum):
    DOMAIN_BEHAVIOR_COMMENT = "domain_behavior_comment"
    TECHNICAL_COMMENT = "technical_comment"
    TODO_COMMENT = "todo_comment"
    GENERATED_FILE_COMMENT = "generated_file_comment"
    DOCSTRING_TECHNICAL = "docstring_technical"
    DOCSTRING_DOMAIN_BEHAVIOR = "docstring_domain_behavior"
    LICENSE_HEADER = "license_header"
    SCAFFOLD_COMMENT = "scaffold_comment"


class EvidenceSourceType(StrEnum):
    BACKEND_CODE = "backend_code"
    FRONTEND_CODE = "frontend_code"
    UNIT_TEST = "unit_test"
    INTEGRATION_TEST = "integration_test"
    API_TEST = "api_test"
    BDD_SPEC = "bdd_spec"
    E2E_TEST = "e2e_test"
    API_CONTRACT = "api_contract"
    DESIGN_DOC = "design_doc"
    TICKET = "ticket"
    README_DOC = "readme_doc"
    CODE_COMMENT = "code_comment"
    COVERAGE_REPORT = "coverage_report"
    RUNTIME_LOG = "runtime_log"
    AUDIT_LOG = "audit_log"
    DOMAIN_EVENT_LOG = "domain_event_log"
    TRACE_SPAN = "trace_span"
    STATIC_ANALYSIS = "static_analysis"
    AI_EXTRACTION = "ai_extraction"


class RuleStatus(StrEnum):
    CANDIDATE = "candidate"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_FOLLOW_UP = "needs_follow_up"
    DEPRECATED = "deprecated"


class CandidateStatus(StrEnum):
    NEEDS_REVIEW = "needs_review"
    PROBABLY_IMPLEMENTATION_DETAIL = "probably_implementation_detail"
    NO_CANDIDATES = "no_candidates"


class ConflictType(StrEnum):
    FRONTEND_BACKEND = "frontend_backend"
    DOCS_CODE = "docs_code"
    TEST_CODE = "test_code"
    API_UI = "api_ui"
    TICKET_CODE = "ticket_code"
    COMMENT_CODE = "comment_code"
    COVERAGE_GAP = "coverage_gap"
    RUNTIME_CODE = "runtime_code"


class RuleConflictStatus(StrEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    ACCEPTED_AS_BUG = "accepted_as_bug"
    ACCEPTED_AS_STALE_DOC = "accepted_as_stale_doc"
    ACCEPTED_AS_FRONTEND_BACKEND_DRIFT = "accepted_as_frontend_backend_drift"
    ACCEPTED_AS_MISSING_TEST = "accepted_as_missing_test"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    IGNORED = "ignored"


class RuleDecisionType(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    DEPRECATE = "deprecate"
    MERGE = "merge"
    NEEDS_FOLLOW_UP = "needs_follow_up"
    EDIT = "edit"
    NOTE = "note"


class ImplementationGapPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImplementationGapStatus(StrEnum):
    OPEN = "open"
    ACCEPTED = "accepted"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    WONT_FIX = "wont_fix"


class SearchEntityType(StrEnum):
    RULE = "rule"
    EVIDENCE = "evidence"
    CLAIM = "claim"
    CONFLICT = "conflict"
    GAP = "gap"
    SOURCE_FILE = "source_file"
    EXPORT = "export"
    SCAN_RUN = "scan_run"


class AuditEventType(StrEnum):
    PROJECT_SETTINGS_CHANGED = "project_settings_changed"
    ANALYSIS_RESET = "analysis_reset"
    RULE_APPROVED = "rule_approved"
    RULE_REJECTED = "rule_rejected"
    EXPORT_GENERATED = "export_generated"
    SCAN_STARTED = "scan_started"
    SCAN_COMPLETED = "scan_completed"
    SCAN_CONFIG_CHANGED = "scan_config_changed"
    PROJECT_MEMBER_CHANGED = "project_member_changed"
    USER_LOGIN = "user_login"
    ANALYSIS_VERSION_ACTIVATED = "analysis_version_activated"
    AI_SUGGESTION_REVIEWED = "ai_suggestion_reviewed"
    RULE_STATUS_CHANGED = "rule_status_changed"
    RULE_EDITED = "rule_edited"
    RULE_REVIEW_NOTE_ADDED = "rule_review_note_added"
    INTEGRATION_CONNECTED = "integration_connected"
    INTEGRATION_ROTATED = "integration_rotated"
    INTEGRATION_DISCONNECTED = "integration_disconnected"
    AI_REMOTE_BLOCKED = "ai_remote_blocked"
    CLAIM_CLUSTER_MERGED = "claim_cluster_merged"
    CLAIM_CLUSTER_SPLIT = "claim_cluster_split"
    CLAIM_CLUSTER_LOCKED = "claim_cluster_locked"
    CLAIM_CLUSTER_UNLOCKED = "claim_cluster_unlocked"
    CLAIM_CLUSTER_REVIEWED = "claim_cluster_reviewed"
    AI_SYNTHESIS_COMPLETED = "ai_synthesis_completed"
    AI_PROVIDER_CONNECTION_CREATED = "ai_provider_connection_created"
    AI_PROVIDER_CONNECTION_UPDATED = "ai_provider_connection_updated"
    AI_PROVIDER_CREDENTIAL_REPLACED = "ai_provider_credential_replaced"
    AI_PROVIDER_CONNECTION_TESTED = "ai_provider_connection_tested"
    AI_PROVIDER_CONNECTION_DISABLED = "ai_provider_connection_disabled"
    AI_PROVIDER_CONNECTION_DELETED = "ai_provider_connection_deleted"
    AI_MODEL_CATALOG_REFRESHED = "ai_model_catalog_refreshed"
    AI_MODEL_COMPATIBILITY_TESTED = "ai_model_compatibility_tested"
    AI_MODEL_ENABLED = "ai_model_enabled"
    AI_MODEL_DISABLED = "ai_model_disabled"
    AI_PROJECT_CONFIG_CHANGED = "ai_project_config_changed"
    AI_PROJECT_FALLBACK_CHANGED = "ai_project_fallback_changed"
    AI_ALLOWED_MODELS_MIGRATED = "ai_allowed_models_migrated"
    AI_GOVERNANCE_UPDATED = "ai_governance_updated"
    PROJECT_ORGANIZATION_ASSIGNED = "project_organization_assigned"
    ORGANIZATION_CREATED = "organization_created"
    PROJECT_CREATED = "project_created"
    GITHUB_REPOSITORY_LINKED = "github_repository_linked"


class IntegrationType(StrEnum):
    GITHUB = "github"
    JIRA = "jira"
    LINEAR = "linear"
    TRELLO = "trello"
    AI_PROVIDER = "ai_provider"


class AIProviderType(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE_GEMINI = "google_gemini"
    AZURE_OPENAI = "azure_openai"
    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"
    DETERMINISTIC_SYNTHESIZER = "deterministic_synthesizer"


class AICredentialSource(StrEnum):
    """How an AI provider connection obtains its API credential.

    Canonical multi-tenant value is ``ssm_secure_string`` (LocalStack/AWS SSM).
    ``encrypted_organization_secret`` remains for legacy Fernet vault rows.
    Legacy DB values ``encrypted_secret`` / ``environment`` are normalized at runtime.
    """

    SSM_SECURE_STRING = "ssm_secure_string"
    ENCRYPTED_ORGANIZATION_SECRET = "encrypted_organization_secret"
    ENVIRONMENT_VARIABLE = "environment_variable"
    MANAGED_IDENTITY = "managed_identity"
    NONE = "none"

    # Backward-compatible aliases (do not use for new writes).
    ENCRYPTED_SECRET = "encrypted_secret"
    ENVIRONMENT = "environment"


class AICredentialConfigStatus(StrEnum):
    """Credential presence/config status surfaced on connection health reads."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    NOT_CONFIGURED = "not_configured"
    ENVIRONMENT_VARIABLE_MISSING = "environment_variable_missing"


class AIConnectionStatus(StrEnum):
    READY = "ready"
    UNTESTED = "untested"
    UNHEALTHY = "unhealthy"
    DISABLED = "disabled"
    MISCONFIGURED = "misconfigured"
    CREDENTIAL_MISSING = "credential_missing"


class AIModelAvailabilityStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNAVAILABLE_FOR_CONNECTION = "unavailable_for_connection"
    ACCESS_DENIED = "access_denied"
    DEPRECATED = "deprecated"
    UNKNOWN = "unknown"
    AVAILABLE_FIXTURE = "available_fixture"
    SETUP_REQUIRED = "setup_required"


class AIModelCompatibilityStatus(StrEnum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    UNTESTED = "untested"
    TEST_FAILED = "test_failed"
    TEST_UNAVAILABLE = "test_unavailable"
    PARTIALLY_COMPATIBLE = "partially_compatible"
    FIXTURE_TESTED = "fixture_tested"


class AICapabilityProbeStatus(StrEnum):
    """Result of an explicit capability probe — distinct from discovery metadata hints."""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class ProjectAiUnavailableReason(StrEnum):
    ACCOUNT_HAS_NO_ORGANIZATION = "account_has_no_organization"
    PROJECT_HAS_NO_ORGANIZATION = "project_has_no_organization"
    ORGANIZATION_ACCESS_DENIED = "organization_access_denied"
    NO_PROVIDER_CONNECTION = "no_provider_connection"
    NO_COMPATIBLE_MODEL = "no_compatible_model"
    PROVIDER_DISABLED = "provider_disabled"
    MODEL_UNAVAILABLE = "model_unavailable"
    LOCAL_BOOTSTRAP_FAILED = "local_bootstrap_failed"


class AIModelLifecycleStatus(StrEnum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"
    UNKNOWN = "unknown"


class AIModelCatalogSource(StrEnum):
    DISCOVERED = "discovered"
    RECOMMENDED_METADATA = "recommended_metadata"
    FIXTURE = "fixture"


class AICompatibilityFailureCategory(StrEnum):
    AUTHENTICATION_FAILED = "authentication_failed"
    CREDENTIAL_MISSING = "credential_missing"
    CREDENTIAL_UNAVAILABLE = "credential_unavailable"
    ACCESS_DENIED = "access_denied"
    MODEL_NOT_FOUND = "model_not_found"
    MODEL_ACCESS_DENIED = "model_access_denied"
    UNSUPPORTED_ENDPOINT = "unsupported_endpoint"
    UNSUPPORTED_RESPONSE_FORMAT = "unsupported_response_format"
    UNSUPPORTED_PARAMETER = "unsupported_parameter"
    PROVIDER_REJECTED_SCHEMA = "provider_rejected_schema"
    TOOL_CALLING_FAILED = "tool_calling_failed"
    STRUCTURED_OUTPUT_FAILED = "structured_output_failed"
    STRUCTURED_PAYLOAD_MISSING = "structured_payload_missing"
    STRUCTURED_PAYLOAD_INVALID = "structured_payload_invalid"
    SCHEMA_VALIDATION_FAILED = "schema_validation_failed"
    RESPONSE_PARSE_FAILED = "response_parse_failed"
    MODEL_REFUSAL = "model_refusal"
    INCOMPLETE_RESPONSE = "incomplete_response"
    MAX_OUTPUT_TOKENS_REACHED = "max_output_tokens_reached"
    CITATION_PRESERVATION_FAILED = "citation_preservation_failed"
    RATE_LIMITED = "rate_limited"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class TicketProviderKey(StrEnum):
    JIRA = "jira"
    TRELLO = "trello"
    FAKE = "fake"


class TicketSyncStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEGRADED = "degraded"


class TicketWebhookDeliveryStatus(StrEnum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class RuntimePrivacyClass(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    REDACTED = "redacted"


class RuntimeRetentionClass(StrEnum):
    SHORT = "short"
    STANDARD = "standard"
    LONG = "long"
    LEGAL_HOLD = "legal_hold"


class RuntimeEventOutcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"
    EXCEPTION = "exception"
    UNKNOWN = "unknown"


class RuntimeProviderKey(StrEnum):
    OTEL = "otel"
    STRUCTURED_LOG = "structured_log"
    AUDIT_LOG = "audit_log"
    PLAIN_TEXT = "plain_text"


class OrganizationRole(StrEnum):
    ORG_ADMIN = "org_admin"
    ORG_MEMBER = "org_member"


class ProjectRole(StrEnum):
    VIEWER = "viewer"
    EDITOR = "editor"
    APPROVER = "approver"
    ADMIN = "admin"


class Permission(StrEnum):
    VIEW = "view"
    EDIT = "edit"
    APPROVE = "approve"
    ADMIN = "admin"
    SCAN = "scan"
    EXPORT = "export"


class AuditEntityType(StrEnum):
    PROJECT = "project"
    RULE = "rule"
    USER = "user"
    EXPORT = "export"
    SCAN_RUN = "scan_run"


class ExportType(StrEnum):
    RULES_MARKDOWN = "rules_markdown"
    GAPS_MARKDOWN = "gaps_markdown"
    CONFLICTS_MARKDOWN = "conflicts_markdown"
    FULL_ATLAS = "full_atlas"


class LineRuleContextRelationship(StrEnum):
    ENFORCES_BEHAVIOR = "enforces_behavior"
    PROVES_BEHAVIOR = "proves_behavior"
    MIRRORS_BEHAVIOR_IN_UI = "mirrors_behavior_in_ui"
    DOCUMENTS_INTENT = "documents_intent"
    REQUESTS_BEHAVIOR = "requests_behavior"
    CONTRADICTS_BEHAVIOR = "contradicts_behavior"
    SUGGESTS_GAP = "suggests_gap"
    OBSERVED_RUNTIME_BEHAVIOR = "observed_runtime_behavior"
    DIRECT_EVIDENCE = "direct_evidence"
    INDIRECT_TRACE = "indirect_trace"


class RuleTraceLinkType(StrEnum):
    IMPLEMENTS = "implements"
    TESTS = "tests"
    DOCUMENTS = "documents"
    CONTRADICTS = "contradicts"


class CoverageAssessmentStatus(StrEnum):
    COVERED = "covered"
    NOT_COVERED = "not_covered"
    PARTIALLY_BRANCH_COVERED = "partially_branch_covered"
    COVERED_BUT_NOT_ASSERTED = "covered_but_not_asserted"
    TESTED_BY_UNIT = "tested_by_unit"
    TESTED_BY_API = "tested_by_api"
    TESTED_BY_BDD = "tested_by_bdd"
    TESTED_BY_E2E = "tested_by_e2e"
    DEAD_OR_UNREACHABLE_SUSPECTED = "dead_or_unreachable_suspected"


class CoverageStatus(StrEnum):
    PENDING = "pending"
    PARSED = "parsed"
    FAILED = "failed"


class RuntimeEvidenceConfidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AiProviderMode(StrEnum):
    STUB = "stub"
    NONE = "none"
    OLLAMA_LOCAL = "ollama_local"
    LLAMACPP_LOCAL = "llamacpp_local"
    OPENAI_REMOTE = "openai_remote"
    HYBRID_LOCAL_FIRST = "hybrid_local_first"


class AiTaskType(StrEnum):
    EVIDENCE_SUMMARY = "evidence_summary"
    RULE_WORDING = "rule_wording"
    CONFLICT_EXPLAIN = "conflict_explain"
    GAP_EXPLAIN = "gap_explain"
    DUPLICATE_CLUSTER_SUMMARY = "duplicate_cluster_summary"


class AiTaskRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AiSuggestionStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class FileTypeMatchType(StrEnum):
    EXTENSION = "extension"
    FILENAME = "filename"
    GLOB = "glob"


class FileKind(StrEnum):
    CODE = "code"
    TEST = "test"
    DOCUMENTATION = "documentation"
    CONFIG = "config"
    DATA = "data"
    SCRIPT = "script"
    BUILD = "build"
    ARTIFACT = "artifact"
    GENERATED = "generated"
    UNKNOWN = "unknown"


class ProductionBucketHint(StrEnum):
    PRODUCTION = "production"
    TESTS = "tests"
    DOCS = "docs"
    CONFIG = "config"
    ARTIFACTS = "artifacts"
    GENERATED_VENDOR = "generated_vendor"
    UNKNOWN = "unknown"


class CommentStyle(StrEnum):
    HASH = "hash"
    SLASH = "slash"
    HTML = "html"
    SQL = "sql"
    YAML = "yaml"
    NONE = "none"
    UNSUPPORTED = "unsupported"


class FileTypeMappingSource(StrEnum):
    BUILT_IN = "built_in"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class ManifestInclusionState(StrEnum):
    INCLUDED = "included"
    EXCLUDED = "excluded"
    UNSUPPORTED = "unsupported"


class ConfigScope(StrEnum):
    SYSTEM = "system"
    ORGANIZATION = "organization"
    PROJECT = "project"
    SCAN = "scan"



class GraphNodeType(StrEnum):
    FILE = "file"
    SYMBOL = "symbol"
    CLASS = "class"
    INTERFACE = "interface"
    METHOD = "method"
    FUNCTION = "function"
    TEST = "test"
    BDD_FEATURE = "bdd_feature"
    BDD_SCENARIO = "bdd_scenario"
    BDD_STEP = "bdd_step"
    DOCUMENT = "document"
    TICKET = "ticket"
    CONFIG_VALUE = "config_value"
    COVERAGE_LOCATION = "coverage_location"
    RUNTIME_EVENT = "runtime_event"
    SOURCE_CLAIM = "source_claim"
    RULE = "rule"


class GraphEdgeType(StrEnum):
    DEFINED_IN = "defined_in"
    CALLS = "calls"
    REFERENCES = "references"
    IMPLEMENTS = "implements"
    INHERITS = "inherits"
    TESTS = "tests"
    ASSERTS = "asserts"
    SPECIFIES = "specifies"
    REQUESTS = "requests"
    EXECUTES = "executes"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    DERIVED_FROM = "derived_from"


class GraphObservationKind(StrEnum):
    NODE = "node"
    EDGE = "edge"
    COMMUNITY = "community"


class GraphResolutionType(StrEnum):
    EXTRACTED = "extracted"
    INFERRED = "inferred"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


class GraphProviderStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    DEGRADED = "degraded"
    FAILED = "failed"
    SKIPPED = "skipped"


class SourceClaimStatus(StrEnum):
    CANDIDATE = "candidate"
    NEEDS_REVIEW = "needs_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class SourceClaimRole(StrEnum):
    IMPLEMENTATION = "implementation"
    VERIFICATION = "verification"
    PRODUCT_INTENT = "product_intent"
    RUNTIME_OBSERVATION = "runtime_observation"
    CONFIGURATION = "configuration"


class TestFramework(StrEnum):
    PYTEST = "pytest"
    UNITTEST = "unittest"
    XUNIT = "xunit"
    NUNIT = "nunit"
    MSTEST = "mstest"
    JEST = "jest"
    VITEST = "vitest"
    PHPUNIT = "phpunit"
    GHERKIN = "gherkin"
    UNKNOWN = "unknown"


class TestAssertionKind(StrEnum):
    ASSERT = "assert"
    EXPECT = "expect"
    EXPECTED_EXCEPTION = "expected_exception"
    MOCK_VERIFY = "mock_verify"
    OTHER = "other"


class TestExecutionStatus(StrEnum):
    UNKNOWN = "unknown"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class BddStepLinkStatus(StrEnum):
    LINKED = "linked"
    AMBIGUOUS = "ambiguous"
    UNDEFINED = "undefined"
    UNCERTAIN = "uncertain"


class BddEvidenceRole(StrEnum):
    PRODUCT_INTENT = "product_intent"
    VERIFICATION = "verification"



class ClaimClusterStatus(StrEnum):
    CANDIDATE = "candidate"
    NEEDS_REVIEW = "needs_review"
    LOCKED = "locked"
    MERGED = "merged"
    SPLIT = "split"
    SUPERSEDED = "superseded"


class ClaimClusterRole(StrEnum):
    """Role of a claim cluster in canonical rule synthesis (distinct from SourceClaimRole)."""

    CANONICAL_RULE = "canonical_rule"
    EXCEPTION = "exception"
    CONTRADICTION = "contradiction"
    SUPERSEDED = "superseded"
    SUPPORTING_EVIDENCE = "supporting_evidence"
    IMPLEMENTATION_DETAIL = "implementation_detail"
    REVIEW_REQUIRED = "review_required"


class CompositePipelineStage(StrEnum):
    MANIFEST = "manifest"
    GRAPH = "graph"
    CLAIMS = "claims"
    CLUSTERS = "clusters"
    AI_SYNTHESIS = "ai_synthesis"
    HEURISTIC_FALLBACK = "heuristic_fallback"
    COMPLETED = "completed"


class CompositePipelineStageStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class AiSynthesisMode(StrEnum):
    FULL = "full"
    NO_AI = "no_ai"
    HEURISTIC_ONLY = "heuristic_only"


class ConflictKind(StrEnum):
    """Semantic conflict classification (v2); distinct from legacy source-pair ConflictType."""

    CONTRADICTION = "contradiction"
    EXCEPTION = "exception"
    SCOPE_DIFFERENCE = "scope_difference"
    SUPERSESSION = "supersession"


class GapType(StrEnum):
    MISSING_IMPLEMENTATION = "missing_implementation"
    MISSING_TEST = "missing_test"
    MISSING_INTENT = "missing_intent"
    MISSING_COVERAGE = "missing_coverage"
    UNOBSERVED_RUNTIME = "unobserved_runtime"


class RuleLineageRelation(StrEnum):
    RENAMED_FROM = "renamed_from"
    MERGED_INTO = "merged_into"
    SPLIT_FROM = "split_from"
    SUPERSEDES = "supersedes"


class CoverageFormat(StrEnum):
    LCOV = "lcov"
    COBERTURA = "cobertura"
    COVERLET = "coverlet"
    JACOCO = "jacoco"
    ISTANBUL = "istanbul"
    CLOVER = "clover"
    UNKNOWN = "unknown"


class SemanticProviderStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    DEGRADED = "degraded"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNAVAILABLE = "unavailable"


__all__ = [
    "AICapabilityProbeStatus",
    "AICompatibilityFailureCategory",
    "AIConnectionStatus",
    "AICredentialConfigStatus",
    "AICredentialSource",
    "AIModelAvailabilityStatus",
    "AIModelCatalogSource",
    "AIModelCompatibilityStatus",
    "AIModelLifecycleStatus",
    "AIProviderType",
    "AiProviderMode",
    "AiSuggestionStatus",
    "AiSynthesisMode",
    "AiSynthesisStatus",
    "AiTaskRunStatus",
    "AiTaskType",
    "AnalysisOutcomeStatus",
    "AnalysisVersionStatus",
    "AuditEntityType",
    "AuditEventType",
    "AuthMode",
    "BddEvidenceRole",
    "BddStepLinkStatus",
    "CandidateStatus",
    "ClaimClusterRole",
    "ClaimClusterStatus",
    "CommentClassification",
    "CommentStyle",
    "CompositePipelineStage",
    "CompositePipelineStageStatus",
    "ConfigScope",
    "ConflictKind",
    "ConflictType",
    "CoverageAssessmentStatus",
    "CoverageFormat",
    "CoverageStatus",
    "DemoMode",
    "EvidenceSourceType",
    "ExportType",
    "ExtractionMethod",
    "ExtractionSkipReason",
    "FileKind",
    "FileTypeMappingSource",
    "FileTypeMatchType",
    "GapType",
    "GraphEdgeType",
    "GraphNodeType",
    "GraphObservationKind",
    "GraphProviderStatus",
    "GraphResolutionType",
    "ImplementationGapPriority",
    "ImplementationGapStatus",
    "IntegrationType",
    "LineRuleContextRelationship",
    "ManifestInclusionState",
    "OrganizationRole",
    "Permission",
    "ProductionBucketHint",
    "ProjectAiUnavailableReason",
    "ProjectEventType",
    "ProjectRole",
    "RelationshipSuggestionStatus",
    "RuleCategory",
    "RuleConflictStatus",
    "RuleDecisionType",
    "RuleLineageRelation",
    "RuleRelationshipType",
    "RuleStatus",
    "RuleTraceLinkType",
    "RuntimeEventOutcome",
    "RuntimeEvidenceConfidence",
    "RuntimePrivacyClass",
    "RuntimeProviderKey",
    "RuntimeRetentionClass",
    "ScanStage",
    "ScanStatus",
    "ScanType",
    "SearchEntityType",
    "SemanticProviderStatus",
    "SourceClaimRole",
    "SourceClaimStatus",
    "SourceFileClassification",
    "SourceLocationType",
    "SourceTreeNodeKind",
    "SourceType",
    "TestAssertionKind",
    "TestExecutionStatus",
    "TestFramework",
    "TicketProviderKey",
    "TicketSyncStatus",
    "TicketWebhookDeliveryStatus",
]
