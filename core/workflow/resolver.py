# Approver Resolver
# Pluggable approver resolution system

"""
Approver Resolver for GOVERNEX+.

Resolves approver types to actual approvers using:
- HR hierarchy integration
- Role ownership tables
- Process ownership registry
- IAM/LDAP lookups
- Custom resolvers

Key Principle:
Resolution is PLUGGABLE - customers can integrate
their own data sources without engine changes.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Protocol
from datetime import datetime
from enum import Enum
import logging

from .models import WorkflowContext, ApproverTypeEnum

logger = logging.getLogger(__name__)


class ApproverSource(Enum):
    """Source of approver information."""
    HR_SYSTEM = "HR_SYSTEM"
    IAM_SYSTEM = "IAM_SYSTEM"
    LDAP = "LDAP"
    ROLE_REGISTRY = "ROLE_REGISTRY"
    PROCESS_REGISTRY = "PROCESS_REGISTRY"
    DATA_CATALOG = "DATA_CATALOG"
    SYSTEM_REGISTRY = "SYSTEM_REGISTRY"
    STATIC_CONFIG = "STATIC_CONFIG"
    CUSTOM = "CUSTOM"


@dataclass
class ResolvedApprover:
    """A resolved approver."""
    approver_id: str
    approver_name: str
    approver_email: str
    approver_type: ApproverTypeEnum
    source: ApproverSource

    # Status
    is_available: bool = True
    is_ooo: bool = False
    ooo_until: Optional[datetime] = None

    # Delegation
    delegate_id: Optional[str] = None
    delegate_name: Optional[str] = None

    # Metadata
    department: str = ""
    title: str = ""
    phone: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approver_id": self.approver_id,
            "approver_name": self.approver_name,
            "approver_email": self.approver_email,
            "approver_type": self.approver_type.value,
            "source": self.source.value,
            "is_available": self.is_available,
            "is_ooo": self.is_ooo,
            "ooo_until": self.ooo_until.isoformat() if self.ooo_until else None,
            "delegate": {
                "id": self.delegate_id,
                "name": self.delegate_name,
            } if self.delegate_id else None,
        }


@dataclass
class ResolutionResult:
    """Result of approver resolution."""
    success: bool = True
    approver: Optional[ResolvedApprover] = None
    fallback_used: bool = False
    fallback_reason: str = ""
    resolution_time_ms: float = 0.0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "approver": self.approver.to_dict() if self.approver else None,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "resolution_time_ms": self.resolution_time_ms,
            "errors": self.errors,
        }


class ApproverResolverProtocol(Protocol):
    """Protocol for approver resolvers."""

    def resolve(
        self,
        context: WorkflowContext,
        **kwargs
    ) -> ResolutionResult:
        """Resolve an approver."""
        ...


# ============================================================
# BUILT-IN RESOLVERS
# ============================================================

class LineManagerResolver:
    """Resolves line manager from HR hierarchy."""

    def __init__(
        self,
        hr_lookup: Optional[Callable[[str], Dict[str, Any]]] = None,
        fallback_id: str = "HR_ADMIN"
    ):
        """
        Initialize resolver.

        Args:
            hr_lookup: Function that takes user_id and returns manager info
            fallback_id: Fallback approver if resolution fails
        """
        self.hr_lookup = hr_lookup
        self.fallback_id = fallback_id

    def resolve(
        self,
        context: WorkflowContext,
        **kwargs
    ) -> ResolutionResult:
        """Resolve line manager for target user."""
        start = datetime.now()
        result = ResolutionResult()

        try:
            user_id = context.target_user_id or context.requester_id

            if self.hr_lookup:
                # Use custom HR lookup
                manager_info = self.hr_lookup(user_id)
                if manager_info:
                    result.approver = ResolvedApprover(
                        approver_id=manager_info.get("id", ""),
                        approver_name=manager_info.get("name", ""),
                        approver_email=manager_info.get("email", ""),
                        approver_type=ApproverTypeEnum.LINE_MANAGER,
                        source=ApproverSource.HR_SYSTEM,
                        is_available=manager_info.get("is_available", True),
                        is_ooo=manager_info.get("is_ooo", False),
                        delegate_id=manager_info.get("delegate_id"),
                        delegate_name=manager_info.get("delegate_name"),
                        department=manager_info.get("department", ""),
                        title=manager_info.get("title", ""),
                    )
                    result.success = True
                else:
                    # Use fallback
                    result.approver = self._create_fallback()
                    result.fallback_used = True
                    result.fallback_reason = "HR lookup returned no manager"
            else:
                # Use manager ID from context
                manager_id = context.target_user_manager_id or context.requester_manager_id
                if manager_id:
                    result.approver = ResolvedApprover(
                        approver_id=manager_id,
                        approver_name=f"Manager ({manager_id})",
                        approver_email=f"{manager_id}@company.com",
                        approver_type=ApproverTypeEnum.LINE_MANAGER,
                        source=ApproverSource.STATIC_CONFIG,
                    )
                    result.success = True
                else:
                    result.approver = self._create_fallback()
                    result.fallback_used = True
                    result.fallback_reason = "No manager ID in context"

        except Exception as e:
            logger.error(f"Line manager resolution failed: {e}")
            result.approver = self._create_fallback()
            result.fallback_used = True
            result.fallback_reason = str(e)
            result.errors.append(str(e))

        result.resolution_time_ms = (datetime.now() - start).total_seconds() * 1000
        return result

    def _create_fallback(self) -> ResolvedApprover:
        """Create fallback approver."""
        return ResolvedApprover(
            approver_id=self.fallback_id,
            approver_name="HR Administrator",
            approver_email=f"{self.fallback_id.lower()}@company.com",
            approver_type=ApproverTypeEnum.LINE_MANAGER,
            source=ApproverSource.STATIC_CONFIG,
        )


class RoleOwnerResolver:
    """Resolves role owner from role registry."""

    def __init__(
        self,
        role_lookup: Optional[Callable[[str], Dict[str, Any]]] = None,
        fallback_id: str = "ROLE_ADMIN"
    ):
        """Initialize resolver."""
        self.role_lookup = role_lookup
        self.fallback_id = fallback_id

    def resolve(
        self,
        context: WorkflowContext,
        **kwargs
    ) -> ResolutionResult:
        """Resolve role owner."""
        start = datetime.now()
        result = ResolutionResult()

        try:
            role_id = context.role_id

            if self.role_lookup and role_id:
                owner_info = self.role_lookup(role_id)
                if owner_info:
                    result.approver = ResolvedApprover(
                        approver_id=owner_info.get("id", ""),
                        approver_name=owner_info.get("name", ""),
                        approver_email=owner_info.get("email", ""),
                        approver_type=ApproverTypeEnum.ROLE_OWNER,
                        source=ApproverSource.ROLE_REGISTRY,
                        is_available=owner_info.get("is_available", True),
                        department=owner_info.get("department", ""),
                    )
                    result.success = True
                else:
                    result.approver = self._create_fallback(role_id)
                    result.fallback_used = True
                    result.fallback_reason = f"No owner found for role {role_id}"
            else:
                result.approver = self._create_fallback(role_id)
                result.fallback_used = True
                result.fallback_reason = "No role lookup configured"

        except Exception as e:
            logger.error(f"Role owner resolution failed: {e}")
            result.approver = self._create_fallback(context.role_id)
            result.fallback_used = True
            result.fallback_reason = str(e)
            result.errors.append(str(e))

        result.resolution_time_ms = (datetime.now() - start).total_seconds() * 1000
        return result

    def _create_fallback(self, role_id: str = "") -> ResolvedApprover:
        """Create fallback approver."""
        return ResolvedApprover(
            approver_id=self.fallback_id,
            approver_name=f"Role Administrator ({role_id})",
            approver_email=f"{self.fallback_id.lower()}@company.com",
            approver_type=ApproverTypeEnum.ROLE_OWNER,
            source=ApproverSource.STATIC_CONFIG,
        )


class ProcessOwnerResolver:
    """Resolves process owner from process registry."""

    def __init__(
        self,
        process_lookup: Optional[Callable[[str], Dict[str, Any]]] = None,
        fallback_id: str = "PROCESS_ADMIN"
    ):
        """Initialize resolver."""
        self.process_lookup = process_lookup
        self.fallback_id = fallback_id

    def resolve(
        self,
        context: WorkflowContext,
        **kwargs
    ) -> ResolutionResult:
        """Resolve process owner."""
        start = datetime.now()
        result = ResolutionResult()

        try:
            process = context.business_process

            if self.process_lookup and process:
                owner_info = self.process_lookup(process)
                if owner_info:
                    result.approver = ResolvedApprover(
                        approver_id=owner_info.get("id", ""),
                        approver_name=owner_info.get("name", ""),
                        approver_email=owner_info.get("email", ""),
                        approver_type=ApproverTypeEnum.PROCESS_OWNER,
                        source=ApproverSource.PROCESS_REGISTRY,
                        department=owner_info.get("department", ""),
                        title=owner_info.get("title", "Process Owner"),
                    )
                    result.success = True
                else:
                    result.approver = self._create_fallback(process)
                    result.fallback_used = True
                    result.fallback_reason = f"No owner found for process {process}"
            else:
                result.approver = self._create_fallback(process)
                result.fallback_used = True
                result.fallback_reason = "No process lookup configured"

        except Exception as e:
            logger.error(f"Process owner resolution failed: {e}")
            result.approver = self._create_fallback(context.business_process)
            result.fallback_used = True
            result.fallback_reason = str(e)
            result.errors.append(str(e))

        result.resolution_time_ms = (datetime.now() - start).total_seconds() * 1000
        return result

    def _create_fallback(self, process: str = "") -> ResolvedApprover:
        """Create fallback approver."""
        return ResolvedApprover(
            approver_id=f"{self.fallback_id}_{process}" if process else self.fallback_id,
            approver_name=f"{process} Process Owner" if process else "Process Administrator",
            approver_email=f"{process.lower()}_owner@company.com" if process else f"{self.fallback_id.lower()}@company.com",
            approver_type=ApproverTypeEnum.PROCESS_OWNER,
            source=ApproverSource.STATIC_CONFIG,
        )


class StaticResolver:
    """Resolves to a static configured approver."""

    def __init__(
        self,
        approver_type: ApproverTypeEnum,
        approver_id: str,
        approver_name: str,
        approver_email: str
    ):
        """Initialize with static values."""
        self.approver_type = approver_type
        self.approver_id = approver_id
        self.approver_name = approver_name
        self.approver_email = approver_email

    def resolve(
        self,
        context: WorkflowContext,
        **kwargs
    ) -> ResolutionResult:
        """Return static approver."""
        return ResolutionResult(
            success=True,
            approver=ResolvedApprover(
                approver_id=self.approver_id,
                approver_name=self.approver_name,
                approver_email=self.approver_email,
                approver_type=self.approver_type,
                source=ApproverSource.STATIC_CONFIG,
            ),
        )


# ============================================================
# RESOLVER REGISTRY
# ============================================================

class ResolverRegistry:
    """
    Registry of approver resolvers.

    Central place to register and manage resolvers.
    Supports hot-swapping resolvers at runtime.
    """

    def __init__(self):
        """Initialize registry."""
        self._resolvers: Dict[ApproverTypeEnum, ApproverResolverProtocol] = {}
        self._init_default_resolvers()

    def _init_default_resolvers(self) -> None:
        """Initialize default resolvers."""
        self._resolvers[ApproverTypeEnum.LINE_MANAGER] = LineManagerResolver()
        self._resolvers[ApproverTypeEnum.ROLE_OWNER] = RoleOwnerResolver()
        self._resolvers[ApproverTypeEnum.PROCESS_OWNER] = ProcessOwnerResolver()

        # Static resolvers for common types
        self._resolvers[ApproverTypeEnum.SECURITY_OFFICER] = StaticResolver(
            ApproverTypeEnum.SECURITY_OFFICER,
            "SECURITY_TEAM",
            "Security Team",
            "security@company.com"
        )
        self._resolvers[ApproverTypeEnum.COMPLIANCE_OFFICER] = StaticResolver(
            ApproverTypeEnum.COMPLIANCE_OFFICER,
            "COMPLIANCE_TEAM",
            "Compliance Team",
            "compliance@company.com"
        )
        self._resolvers[ApproverTypeEnum.CISO] = StaticResolver(
            ApproverTypeEnum.CISO,
            "CISO",
            "Chief Information Security Officer",
            "ciso@company.com"
        )
        self._resolvers[ApproverTypeEnum.FIREFIGHTER_SUPERVISOR] = StaticResolver(
            ApproverTypeEnum.FIREFIGHTER_SUPERVISOR,
            "FF_SUPERVISOR",
            "Firefighter Supervisor",
            "ff_supervisor@company.com"
        )
        self._resolvers[ApproverTypeEnum.GOVERNANCE_DESK] = StaticResolver(
            ApproverTypeEnum.GOVERNANCE_DESK,
            "GOVERNANCE_DESK",
            "Governance Desk",
            "governance@company.com"
        )

    def register(
        self,
        approver_type: ApproverTypeEnum,
        resolver: ApproverResolverProtocol
    ) -> None:
        """Register a resolver for an approver type."""
        self._resolvers[approver_type] = resolver
        logger.info(f"Registered resolver for {approver_type.value}")

    def unregister(self, approver_type: ApproverTypeEnum) -> None:
        """Unregister a resolver."""
        if approver_type in self._resolvers:
            del self._resolvers[approver_type]
            logger.info(f"Unregistered resolver for {approver_type.value}")

    def get_resolver(
        self,
        approver_type: ApproverTypeEnum
    ) -> Optional[ApproverResolverProtocol]:
        """Get resolver for an approver type."""
        return self._resolvers.get(approver_type)

    def resolve(
        self,
        approver_type: ApproverTypeEnum,
        context: WorkflowContext,
        **kwargs
    ) -> ResolutionResult:
        """
        Resolve an approver using the registered resolver.

        Args:
            approver_type: Type of approver to resolve
            context: Workflow context
            **kwargs: Additional arguments for resolver

        Returns:
            ResolutionResult
        """
        resolver = self._resolvers.get(approver_type)

        if not resolver:
            logger.warning(f"No resolver for {approver_type.value}, using fallback")
            return ResolutionResult(
                success=True,
                approver=ResolvedApprover(
                    approver_id=f"UNKNOWN_{approver_type.value}",
                    approver_name=approver_type.value,
                    approver_email=f"{approver_type.value.lower()}@company.com",
                    approver_type=approver_type,
                    source=ApproverSource.STATIC_CONFIG,
                ),
                fallback_used=True,
                fallback_reason="No resolver registered",
            )

        return resolver.resolve(context, **kwargs)

    def resolve_all(
        self,
        approver_types: List[ApproverTypeEnum],
        context: WorkflowContext
    ) -> Dict[ApproverTypeEnum, ResolutionResult]:
        """Resolve multiple approver types."""
        return {
            atype: self.resolve(atype, context)
            for atype in approver_types
        }

    def list_resolvers(self) -> List[Dict[str, Any]]:
        """List all registered resolvers."""
        return [
            {
                "approver_type": atype.value,
                "resolver_class": type(resolver).__name__,
            }
            for atype, resolver in self._resolvers.items()
        ]


# ============================================================
# MAIN RESOLVER CLASS
# ============================================================

class ApproverResolver:
    """
    Main approver resolution class.

    Wraps ResolverRegistry with convenience methods.
    """

    def __init__(self, registry: Optional[ResolverRegistry] = None):
        """Initialize resolver."""
        self.registry = registry or ResolverRegistry()

    def resolve(
        self,
        approver_type: ApproverTypeEnum,
        context: WorkflowContext
    ) -> ResolvedApprover:
        """
        Resolve an approver.

        Returns the resolved approver (or fallback).
        """
        result = self.registry.resolve(approver_type, context)
        return result.approver

    def resolve_with_details(
        self,
        approver_type: ApproverTypeEnum,
        context: WorkflowContext
    ) -> ResolutionResult:
        """Resolve with full result details."""
        return self.registry.resolve(approver_type, context)

    def configure_hr_integration(
        self,
        lookup_function: Callable[[str], Dict[str, Any]]
    ) -> None:
        """Configure HR system integration for manager lookup."""
        self.registry.register(
            ApproverTypeEnum.LINE_MANAGER,
            LineManagerResolver(hr_lookup=lookup_function)
        )

    def configure_role_registry(
        self,
        lookup_function: Callable[[str], Dict[str, Any]]
    ) -> None:
        """Configure role registry integration."""
        self.registry.register(
            ApproverTypeEnum.ROLE_OWNER,
            RoleOwnerResolver(role_lookup=lookup_function)
        )

    def configure_process_registry(
        self,
        lookup_function: Callable[[str], Dict[str, Any]]
    ) -> None:
        """Configure process registry integration."""
        self.registry.register(
            ApproverTypeEnum.PROCESS_OWNER,
            ProcessOwnerResolver(process_lookup=lookup_function)
        )

    def configure_static_approver(
        self,
        approver_type: ApproverTypeEnum,
        approver_id: str,
        approver_name: str,
        approver_email: str
    ) -> None:
        """Configure a static approver."""
        self.registry.register(
            approver_type,
            StaticResolver(approver_type, approver_id, approver_name, approver_email)
        )
