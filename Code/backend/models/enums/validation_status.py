from enum import Enum


class ValidationStatus(Enum):
    INFERRED = "inferred"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    USER_EDITED = "user_edited"
