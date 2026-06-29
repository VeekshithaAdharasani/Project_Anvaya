from enum import Enum


class RelationshipType(Enum):
    MOTIVATES = "motivates"
    REQUIRES = "requires"
    SUPPORTS = "supports"
    INFLUENCES = "influences"
    STRENGTHENS = "strengthens"
