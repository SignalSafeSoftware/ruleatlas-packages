"""Pure AI synthesis domain: proposal schema, validation, migration, and wording."""

from ruleatlas_ai.synthesis.ast_proposal import (
    AST_RULE_PROPOSAL_KIND,
    AST_RULE_SCHEMA_VERSION,
    AstRuleEvidenceCitation,
    AstRuleField,
    AstRuleProposal,
    ProductIntentStatus,
    RuleEvidenceRole,
    ast_proposal_json_schema,
    validate_ast_proposal_payload,
)
from ruleatlas_ai.synthesis.ast_proposal_validation import (
    AstProposalValidationCode,
    AstProposalValidationIssue,
    AstProposalValidationResult,
    validate_ast_rule_proposal,
)
from ruleatlas_ai.synthesis.claims_normalization import (
    AST_PROPOSAL_VALIDATOR_KEY,
    AST_PROPOSAL_VALIDATOR_VERSION,
    prepare_validated_ast_proposal_input,
)
from ruleatlas_ai.synthesis.proposal_migration import (
    LegacyProposalMigrationContext,
    migrate_legacy_proposal,
)
from ruleatlas_ai.synthesis.schema import (
    AI_RULE_SCHEMA_VERSION,
    AiRuleProposal,
    proposal_json_schema,
    validate_proposal_payload,
)

__all__ = [
    "AI_RULE_SCHEMA_VERSION",
    "AST_PROPOSAL_VALIDATOR_KEY",
    "AST_PROPOSAL_VALIDATOR_VERSION",
    "AST_RULE_PROPOSAL_KIND",
    "AST_RULE_SCHEMA_VERSION",
    "AiRuleProposal",
    "AstProposalValidationCode",
    "AstProposalValidationIssue",
    "AstProposalValidationResult",
    "AstRuleEvidenceCitation",
    "AstRuleField",
    "AstRuleProposal",
    "LegacyProposalMigrationContext",
    "ProductIntentStatus",
    "RuleEvidenceRole",
    "ast_proposal_json_schema",
    "migrate_legacy_proposal",
    "prepare_validated_ast_proposal_input",
    "proposal_json_schema",
    "validate_ast_proposal_payload",
    "validate_ast_rule_proposal",
    "validate_proposal_payload",
]
