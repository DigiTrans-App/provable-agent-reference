class ProvableAgentError(ValueError):
    """Base error for deterministic reference-contract failures."""


class ContractError(ProvableAgentError):
    """Raised when an input violates a public contract."""


class CompilationError(ProvableAgentError):
    """Raised when trusted compilation cannot construct a canonical candidate."""


class VerificationError(ProvableAgentError):
    """Raised when a verification-dependent action is attempted after failure."""


class ApprovalError(ProvableAgentError):
    """Raised when approval is missing, invalid, or bound to a different candidate."""


class AuthorizationError(ProvableAgentError):
    """Raised when an exact-use authorization cannot be issued."""
