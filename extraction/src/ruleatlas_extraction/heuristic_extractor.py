from __future__ import annotations

import hashlib
import re

from ruleatlas_contracts.classification.scaffold_filter import (
    find_domain_test_blocks,
    find_test_evidence_lines,
    is_non_business_rule_scaffold_line,
    is_package_marker_path,
    is_potential_business_behavior_line,
    is_scaffold_evidence_text,
)
from ruleatlas_contracts.enums import (
    CandidateStatus,
    EvidenceSourceType,
    SourceFileClassification,
    SourceType,
)
from ruleatlas_persistence.models import SourceFile

from ruleatlas_extraction.comment_classifier import (
    code_text_without_comments,
    find_domain_comment_candidates,
)
from ruleatlas_extraction.schemas import ExtractionCandidate, ExtractionEvidence

BACKEND_POLICY_KEYWORDS = (
    "permission",
    "auth",
    "role",
    "status",
    "expiry",
    "expired",
    "deleted",
    "report",
)
DOC_POLICY_KEYWORDS = ("must", "should", "cannot", "only", "admin", "manager", "expires")
BDD_SCENARIO_PATTERN = re.compile(r"^\s*Scenario:\s*(.+)$", re.MULTILINE)
BDD_STEP_PATTERN = re.compile(r"^\s*(Given|When|Then|And)\s+(.+)$", re.MULTILINE)
BDD_KEYWORD_LINE_PATTERN = re.compile(r"^\s*(Given|When|Then|And|But)\s+(.+)$", re.IGNORECASE)
OPENAPI_HINT_PATTERN = re.compile(r'"openapi"|"swagger"|"paths"\s*:', re.IGNORECASE)
CONFIG_FILE_NAMES = {
    "pyproject.toml",
    "package.json",
    "tsconfig.json",
    "docker-compose.yml",
    "poetry.lock",
    "package-lock.json",
}
STYLE_EXTENSIONS = {".css", ".scss", ".sass", ".less"}
HEALTH_OR_FRAMEWORK_PATH_MARKERS = (
    "/health",
    "health.py",
    "health.ts",
    "health.js",
    "routers/health",
    "vitest.shared",
    "vitest.config",
    "__init__.py",
)
MAX_HEURISTIC_CONFIDENCE = 45.0
LOW_CONFIDENCE = 25.0
COMMENT_CONFIDENCE = 18.0


def _line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _first_match_line(text: str, keywords: tuple[str, ...]) -> int | None:
    lowered = text.lower()
    for keyword in keywords:
        idx = lowered.find(keyword)
        if idx >= 0:
            return _line_number(text, idx)
    return None


def _first_domain_bearing_line(text: str) -> int | None:
    """Return the first non-scaffold line that clearly signals business behavior."""
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        if is_non_business_rule_scaffold_line(stripped, file_text=text, line_number=line_number):
            continue
        if is_potential_business_behavior_line(stripped):
            return line_number
    return None


def _snippet_around_line(text: str, line: int, radius: int = 2) -> str:
    lines = text.splitlines()
    if not lines:
        return ""
    start = max(line - 1 - radius, 0)
    end = min(line + radius, len(lines))
    return "\n".join(lines[start:end])


def _claim_from_line(text: str, line: int, fallback: str = "") -> str:
    lines = text.splitlines()
    if 1 <= line <= len(lines):
        content = lines[line - 1].strip()
        if (
            content
            and not content.startswith("#")
            and not is_non_business_rule_scaffold_line(content)
            and not is_scaffold_evidence_text(content)
        ):
            return content
        if line < len(lines):
            next_line = lines[line].strip()
            if (
                next_line
                and not next_line.startswith("#")
                and not is_non_business_rule_scaffold_line(next_line)
                and not is_scaffold_evidence_text(next_line)
            ):
                return next_line
    return fallback


def _is_health_or_framework_path(path: str) -> bool:
    lowered = path.lower().replace("\\", "/")
    if is_package_marker_path(lowered):
        return True
    return any(marker in lowered for marker in HEALTH_OR_FRAMEWORK_PATH_MARKERS)


def _is_generic_config(path: str) -> bool:
    name = path.rsplit("/", maxsplit=1)[-1].lower()
    if name in CONFIG_FILE_NAMES:
        return True
    return name.endswith((".json", ".yaml", ".yml", ".toml", ".ini", ".env"))


def _is_style_only(source_file: SourceFile) -> bool:
    if source_file.classification == SourceFileClassification.PRESENTATION_ONLY:
        return True
    return any(source_file.path.lower().endswith(ext) for ext in STYLE_EXTENSIONS)


class HeuristicRuleCandidateExtractor:
    def extract(self, source_file: SourceFile, text: str) -> list[ExtractionCandidate]:
        if not text.strip():
            return []
        if _is_style_only(source_file) or _is_generic_config(source_file.path):
            return []
        if is_package_marker_path(source_file.path) or _is_health_or_framework_path(source_file.path):
            return []

        lowered = text.lower()
        path = source_file.path

        if _is_api_contract_file(path, text):
            return self._extract_api_contract_candidate(text, path)

        if source_file.source_type in {SourceType.BACKEND_CODE, SourceType.FRONTEND_CODE}:
            candidates = self._extract_code_candidate(source_file, text, path)
            candidates.extend(self._extract_comment_candidates(text, path))
            return candidates

        if path.lower().endswith(".feature") or source_file.source_type == SourceType.BDD_SPECS:
            return self._extract_bdd_candidate(text, path)

        if source_file.source_type in {SourceType.TESTS, SourceType.BDD_SPECS}:
            candidates = self._extract_test_candidate(text, path)
            candidates.extend(self._extract_comment_candidates(text, path))
            return candidates

        if source_file.source_type == SourceType.API_CONTRACT or _is_api_contract_file(path, text):
            return self._extract_api_contract_candidate(text, path)

        if source_file.source_type in {
            SourceType.DOCS,
            SourceType.DESIGN_DOCS,
            SourceType.TICKETS,
        }:
            return self._extract_doc_candidate(text, lowered, path)

        return []

    def _extract_code_candidate(
        self,
        source_file: SourceFile,
        text: str,
        path: str,
    ) -> list[ExtractionCandidate]:
        if _is_health_or_framework_path(path):
            return []

        code_text = code_text_without_comments(text)
        code_lowered = code_text.lower()
        if not any(keyword in code_lowered for keyword in BACKEND_POLICY_KEYWORDS):
            return []

        line = _first_domain_bearing_line(code_text) or _first_match_line(code_text, BACKEND_POLICY_KEYWORDS) or 1
        claim = _claim_from_line(code_text, line, "")
        if not claim or is_non_business_rule_scaffold_line(claim) or is_scaffold_evidence_text(claim):
            return []
        evidence = ExtractionEvidence(
            source_type=EvidenceSourceType.BACKEND_CODE
            if source_file.source_type == SourceType.BACKEND_CODE
            else EvidenceSourceType.FRONTEND_CODE,
            reference_path=path,
            start_line=line,
            end_line=line,
            snippet=_snippet_around_line(code_text, line),
            claim_text=claim,
            confidence_score=LOW_CONFIDENCE,
            extraction_explanation="Stub extractor matched conservative backend policy keywords.",
        )
        return [
            ExtractionCandidate(
                domain="access_control",
                name=f"Policy candidate in {path}",
                business_rule=claim,
                why_this_rule_exists="Source contains policy-like authorization or lifecycle language.",
                confidence_score=LOW_CONFIDENCE,
                candidate_status=CandidateStatus.NEEDS_REVIEW,
                evidence=[evidence],
                is_likely_implementation_detail=False,
            )
        ]

    def _extract_comment_candidates(
        self,
        text: str,
        path: str,
    ) -> list[ExtractionCandidate]:
        candidates: list[ExtractionCandidate] = []
        for block, claim, classification in find_domain_comment_candidates(text):
            evidence = ExtractionEvidence(
                source_type=EvidenceSourceType.CODE_COMMENT,
                reference_path=path,
                start_line=block.start_line,
                end_line=block.end_line,
                snippet=_snippet_for_block(text, block.start_line, block.end_line),
                claim_text=claim,
                confidence_score=COMMENT_CONFIDENCE,
                extraction_explanation=(
                    f"Comment classified as {classification.value}; weak product-intent hint only."
                ),
            )
            candidates.append(
                ExtractionCandidate(
                    domain="product_policy",
                    name=f"Comment evidence in {path}",
                    business_rule=claim,
                    why_this_rule_exists=(
                        "Comment/docstring describes domain behavior but cannot confirm a rule alone."
                    ),
                    confidence_score=COMMENT_CONFIDENCE,
                    candidate_status=CandidateStatus.NEEDS_REVIEW,
                    evidence=[evidence],
                    is_likely_implementation_detail=False,
                )
            )
        return candidates

    def _extract_bdd_candidate(
        self,
        text: str,
        path: str,
    ) -> list[ExtractionCandidate]:
        scenario = BDD_SCENARIO_PATTERN.search(text)
        best_step, best_line = _pick_bdd_domain_step(text)

        scenario_name = scenario.group(1).strip() if scenario else None
        if scenario_name and is_non_business_rule_scaffold_line(scenario_name):
            scenario_name = None
        if scenario_name and is_scaffold_evidence_text(scenario_name):
            scenario_name = None
        scenario_has_domain = (
            scenario_name is not None
            and is_potential_business_behavior_line(scenario_name)
            and not is_non_business_rule_scaffold_line(scenario_name)
        )

        if scenario is None and best_step is None:
            return []

        if scenario_has_domain:
            assert scenario is not None
            line = _line_number(text, scenario.start())
            if best_step is not None:
                claim = f"BDD scenario '{scenario_name}': {best_step}"
            else:
                claim = f"BDD scenario '{scenario_name}'"
        elif best_step is not None and is_potential_business_behavior_line(best_step):
            if is_non_business_rule_scaffold_line(best_step) or is_scaffold_evidence_text(best_step):
                return []
            line = best_line
            title = scenario_name or "Unnamed scenario"
            claim = f"BDD scenario '{title}': {best_step}"
        else:
            return []

        if is_non_business_rule_scaffold_line(claim) or is_scaffold_evidence_text(claim):
            return []

        evidence = ExtractionEvidence(
            source_type=EvidenceSourceType.BDD_SPEC,
            reference_path=path,
            start_line=line,
            end_line=line,
            snippet=_snippet_around_line(text, line),
            claim_text=claim,
            confidence_score=MAX_HEURISTIC_CONFIDENCE,
            extraction_explanation="Parsed BDD feature scenario/step as product/test evidence.",
        )
        return [
            ExtractionCandidate(
                domain="product_policy",
                name=f"BDD scenario in {path}",
                business_rule=claim,
                why_this_rule_exists="BDD scenarios document expected product behavior.",
                confidence_score=MAX_HEURISTIC_CONFIDENCE,
                candidate_status=CandidateStatus.NEEDS_REVIEW,
                evidence=[evidence],
            )
        ]

    def _extract_api_contract_candidate(
        self,
        text: str,
        path: str,
    ) -> list[ExtractionCandidate]:
        if not OPENAPI_HINT_PATTERN.search(text):
            return []
        status_match = re.search(r'"(\d{3})"\s*:', text)
        auth_match = re.search(r'"security"\s*:', text)
        line = _first_match_line(text, ("401", "403", "422", "security", "responses")) or 1
        claim_parts = [f"API contract candidate in {path}"]
        if status_match:
            claim_parts.append(f"documents status {status_match.group(1)}")
        if auth_match:
            claim_parts.append("defines security requirements")
        claim = "; ".join(claim_parts)
        evidence = ExtractionEvidence(
            source_type=EvidenceSourceType.API_CONTRACT,
            reference_path=path,
            start_line=line,
            end_line=line,
            snippet=_snippet_around_line(text, line),
            claim_text=claim,
            confidence_score=LOW_CONFIDENCE,
            extraction_explanation="Stub extractor matched OpenAPI contract markers.",
        )
        return [
            ExtractionCandidate(
                domain="api_contract",
                name=f"API contract in {path}",
                business_rule=claim,
                why_this_rule_exists="OpenAPI contracts describe API behavior constraints.",
                confidence_score=LOW_CONFIDENCE,
                candidate_status=CandidateStatus.NEEDS_REVIEW,
                evidence=[evidence],
            )
        ]

    def _extract_test_candidate(
        self,
        text: str,
        path: str,
    ) -> list[ExtractionCandidate]:
        # Domain-behavior gate: only unit tests with product/domain signals become candidates.
        # Technical helper/utility/smoke tests are skipped entirely (not needs-review).
        blocks = find_domain_test_blocks(text, path=path)
        if not blocks:
            evidence_lines = find_test_evidence_lines(text, path=path)
            if not evidence_lines:
                return []
            line, claim_line = evidence_lines[0]
            blocks = [(line, line, claim_line)]

        start_line, end_line, claim_line = blocks[0]
        claim = claim_line
        if not claim.startswith(("Unit test ", "Test asserts")):
            if is_potential_business_behavior_line(claim_line) or claim_line.startswith("test_"):
                claim = (
                    claim_line
                    if not claim_line.startswith("test_")
                    else f"Unit test {claim_line} in {path} exercises expected behavior."
                )
            else:
                claim = _claim_from_line(
                    text,
                    start_line,
                    f"Test asserts expected behavior in {path}: {claim_line}",
                )

        if is_non_business_rule_scaffold_line(claim) or is_scaffold_evidence_text(claim):
            return []

        evidence = ExtractionEvidence(
            source_type=EvidenceSourceType.UNIT_TEST,
            reference_path=path,
            start_line=start_line,
            end_line=max(end_line, start_line),
            snippet=_snippet_around_line(text, start_line, radius=max(2, end_line - start_line + 1)),
            claim_text=claim,
            confidence_score=MAX_HEURISTIC_CONFIDENCE,
            extraction_explanation="Stub extractor found domain-bearing test assertion or scenario.",
        )
        return [
            ExtractionCandidate(
                domain="testing",
                name=f"Test evidence in {path}",
                business_rule=claim,
                why_this_rule_exists="Tests may prove behavior but do not alone confirm product intent.",
                confidence_score=MAX_HEURISTIC_CONFIDENCE,
                candidate_status=CandidateStatus.NEEDS_REVIEW,
                evidence=[evidence],
            )
        ]

    def _extract_doc_candidate(
        self,
        text: str,
        lowered: str,
        path: str,
    ) -> list[ExtractionCandidate]:
        if not any(keyword in lowered for keyword in DOC_POLICY_KEYWORDS):
            return []

        line = _first_match_line(text, DOC_POLICY_KEYWORDS) or 1
        claim = _claim_from_line(
            text,
            line,
            f"Documented policy language detected in {path}; review stated product constraints.",
        )
        evidence = ExtractionEvidence(
            source_type=EvidenceSourceType.README_DOC,
            reference_path=path,
            start_line=line,
            end_line=line,
            snippet=_snippet_around_line(text, line),
            claim_text=claim,
            confidence_score=MAX_HEURISTIC_CONFIDENCE,
            extraction_explanation="Stub extractor matched documented policy modal language.",
        )
        return [
            ExtractionCandidate(
                domain="product_policy",
                name=f"Documented policy in {path}",
                business_rule=claim,
                why_this_rule_exists="Documentation states product intent using policy modal language.",
                confidence_score=MAX_HEURISTIC_CONFIDENCE,
                candidate_status=CandidateStatus.NEEDS_REVIEW,
                evidence=[evidence],
            )
        ]


def _pick_bdd_domain_step(text: str) -> tuple[str | None, int]:
    """Prefer Then/When/And steps with domain behavior; fall back to first non-scaffold step.

    Returns (step_text, line_number). If no usable step exists, returns (None, 0).
    """
    best_domain: tuple[str, int, int] | None = None
    fallback: tuple[str, int, int] | None = None
    keyword_priority = {"then": 4, "when": 2, "and": 3, "but": 2, "given": 1}
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = BDD_KEYWORD_LINE_PATTERN.match(line)
        if match is None:
            continue
        keyword = match.group(1).strip().lower()
        step_text = match.group(2).strip()
        if is_non_business_rule_scaffold_line(f"{keyword.capitalize()} {step_text}"):
            continue
        priority = keyword_priority.get(keyword, 1)
        if is_potential_business_behavior_line(step_text):
            if best_domain is None or priority > best_domain[2]:
                best_domain = (step_text, line_number, priority)
        elif fallback is None and keyword != "given":
            fallback = (step_text, line_number, priority)
    if best_domain is not None:
        return best_domain[0], best_domain[1]
    if fallback is not None:
        return fallback[0], fallback[1]
    return None, 0


def _snippet_for_block(text: str, start_line: int, end_line: int, radius: int = 1) -> str:
    lines = text.splitlines()
    if not lines:
        return ""
    start = max(start_line - 1 - radius, 0)
    end = min(end_line + radius, len(lines))
    return "\n".join(lines[start:end])


def _is_api_contract_file(path: str, text: str) -> bool:
    lowered = path.lower()
    if any(token in lowered for token in ("openapi", "swagger", "api-spec", "api_spec")):
        return True
    return bool(OPENAPI_HINT_PATTERN.search(text))


def stable_key_for_candidate(candidate: ExtractionCandidate) -> str:
    normalized = candidate.business_rule.strip().lower()
    domain = (candidate.domain or "general").strip().lower()
    digest = hashlib.sha256(f"{domain}:{normalized}".encode()).hexdigest()
    return digest[:32]
