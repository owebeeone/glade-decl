"""Additive assistance data module v1; no runtime or product policy.

Application payloads are opaque UTF-8 JSON bytes. Normal exchange correlation
belongs to Glade, so no command/receipt identity or recovery record is defined.
The existing declaration v1 and retired AdvertisementRecord are untouched.
"""
from taut.ir.dsl import BYTES, INT, STR, F, Msg, Ref, schema

SCHEMA = schema(
    Msg('AssistanceIdentity',
        F('application', 1, STR), F('workspace', 2, STR),
        F('supplier', 3, STR), F('generation', 4, STR)),
    Msg('AssistanceAdvertisement',
        F('version', 1, INT), F('identity', 2, Ref('AssistanceIdentity')),
        F('share', 3, STR), F('label', 4, STR), F('capabilities', 5, BYTES),
        F('expires', 6, INT)),
    Msg('AssistanceRequest',
        F('version', 1, INT), F('identity', 2, Ref('AssistanceIdentity')),
        F('consumer', 3, STR), F('operation', 4, STR), F('deadline', 5, INT),
        F('token', 6, STR, optional=True), F('epoch', 7, INT, optional=True),
        F('payload', 8, BYTES)),
    Msg('AssistanceResult',
        F('status', 1, STR), F('token', 2, STR, optional=True),
        F('epoch', 3, INT, optional=True), F('expires', 4, INT, optional=True),
        F('reason', 5, STR, optional=True), F('payload', 6, BYTES)),
)
