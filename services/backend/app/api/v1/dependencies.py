"""Versioned route dependencies."""

from typing import cast

from fastapi import Request
from voicecrm_contracts import CrmPort


def get_crm(request: Request) -> CrmPort:
    return cast(CrmPort, request.app.state.crm)
