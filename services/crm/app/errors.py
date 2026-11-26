"""CRM adapter errors independent from any specific provider."""


class CrmError(Exception):
    """Base exception for CRM operations."""


class CrmAuthenticationError(CrmError):
    """Authentication failed or the integration user lacks access."""


class CrmRequestError(CrmError):
    """Salesforce rejected a request or returned an unexpected response."""


class CrmNotFoundError(CrmError):
    """The requested CRM record does not exist or is not accessible."""
