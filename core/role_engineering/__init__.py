# Role Engineering Module
from .designer import (
    RoleDesigner, Role, RoleType, RoleStatus,
    Permission, PermissionType, AuthorizationObject, RoleVersion
)
from .business_roles import (
    BusinessRoleManager, BusinessRole, BusinessRoleStatus, ApprovalRequirement,
    TechnicalRoleMapping, RoleCatalogEntry, RoleOwnership
)
from .analyzer import (
    RoleAnalyzer, RoleComparison, RoleOptimization,
    PermissionGap, RoleConflict
)

__all__ = [
    "RoleDesigner",
    "Role",
    "RoleType",
    "RoleStatus",
    "Permission",
    "PermissionType",
    "AuthorizationObject",
    "RoleVersion",
    "BusinessRoleManager",
    "BusinessRole",
    "BusinessRoleStatus",
    "ApprovalRequirement",
    "TechnicalRoleMapping",
    "RoleCatalogEntry",
    "RoleOwnership",
    "RoleAnalyzer",
    "RoleComparison",
    "RoleOptimization",
    "PermissionGap",
    "RoleConflict"
]
