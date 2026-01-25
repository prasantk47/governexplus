"""
Provisioning Engine

Core engine for executing provisioning operations across connected systems.
Handles user creation, role assignment, and access management.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import logging
import asyncio
import uuid

from core.connectors import ConnectorFactory, connector_factory, BaseConnector

logger = logging.getLogger(__name__)


class ProvisioningStatus(Enum):
    """Status of a provisioning task"""
    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"
    CANCELLED = "cancelled"
    RETRY_SCHEDULED = "retry_scheduled"


class ProvisioningAction(Enum):
    """Types of provisioning actions"""
    CREATE_USER = "create_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"
    LOCK_USER = "lock_user"
    UNLOCK_USER = "unlock_user"
    RESET_PASSWORD = "reset_password"
    ASSIGN_ROLE = "assign_role"
    REMOVE_ROLE = "remove_role"
    SYNC_USER = "sync_user"


@dataclass
class ProvisioningStep:
    """A single step in a provisioning task"""
    step_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    action: ProvisioningAction = ProvisioningAction.ASSIGN_ROLE
    target_system: str = ""
    target_user: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Execution status
    status: ProvisioningStatus = ProvisioningStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Dict] = None

    # Retry handling
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict:
        return {
            "step_id": self.step_id,
            "action": self.action.value,
            "target_system": self.target_system,
            "target_user": self.target_user,
            "parameters": self.parameters,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "result": self.result,
            "retry_count": self.retry_count
        }


@dataclass
class ProvisioningTask:
    """
    A provisioning task containing one or more steps.

    Represents a complete provisioning workflow for a request.
    """
    task_id: str = field(default_factory=lambda: f"PROV-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}")

    # Source reference
    source_type: str = ""  # access_request, jml_event, certification, etc.
    source_id: str = ""  # Reference ID of source

    # User context
    user_id: str = ""
    user_name: str = ""
    requestor_id: str = ""

    # Task details
    description: str = ""
    priority: int = 5  # 1-10, higher = more urgent
    steps: List[ProvisioningStep] = field(default_factory=list)

    # Status tracking
    status: ProvisioningStatus = ProvisioningStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    error_summary: Optional[str] = None

    # Callbacks
    callback_url: Optional[str] = None

    def __post_init__(self):
        self.total_steps = len(self.steps)

    def add_step(self, step: ProvisioningStep):
        """Add a step to the task"""
        self.steps.append(step)
        self.total_steps = len(self.steps)

    def calculate_progress(self) -> Dict:
        """Calculate task progress"""
        self.completed_steps = sum(1 for s in self.steps if s.status == ProvisioningStatus.COMPLETED)
        self.failed_steps = sum(1 for s in self.steps if s.status == ProvisioningStatus.FAILED)
        pending = sum(1 for s in self.steps if s.status == ProvisioningStatus.PENDING)

        progress = 0
        if self.total_steps > 0:
            progress = round((self.completed_steps / self.total_steps) * 100, 1)

        return {
            "total": self.total_steps,
            "completed": self.completed_steps,
            "failed": self.failed_steps,
            "pending": pending,
            "progress_percent": progress
        }

    def to_dict(self) -> Dict:
        progress = self.calculate_progress()
        return {
            "task_id": self.task_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "requestor_id": self.requestor_id,
            "description": self.description,
            "priority": self.priority,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": progress,
            "steps": [s.to_dict() for s in self.steps],
            "error_summary": self.error_summary
        }

    def to_summary(self) -> Dict:
        """Brief summary for list views"""
        progress = self.calculate_progress()
        return {
            "task_id": self.task_id,
            "user_name": self.user_name,
            "description": self.description,
            "status": self.status.value,
            "progress_percent": progress["progress_percent"],
            "created_at": self.created_at.isoformat()
        }


class ProvisioningEngine:
    """
    Main provisioning engine.

    Executes provisioning tasks by coordinating with system connectors.
    """

    def __init__(self, connector_factory: ConnectorFactory):
        self.connector_factory = connector_factory
        self._tasks: Dict[str, ProvisioningTask] = {}
        self._running = False
        self._callbacks: Dict[str, List[Callable]] = {
            "on_task_start": [],
            "on_task_complete": [],
            "on_step_complete": [],
            "on_error": []
        }
        self._lock = asyncio.Lock()

    def register_callback(self, event: str, callback: Callable):
        """Register a callback for provisioning events"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _trigger_callbacks(self, event: str, *args, **kwargs):
        """Trigger registered callbacks"""
        for callback in self._callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(*args, **kwargs))
                else:
                    callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")

    async def submit_task(self, task: ProvisioningTask) -> str:
        """
        Submit a provisioning task for execution.

        Returns the task ID for tracking.
        """
        async with self._lock:
            self._tasks[task.task_id] = task

        logger.info(f"Submitted provisioning task: {task.task_id} with {task.total_steps} steps")
        return task.task_id

    async def execute_task(self, task_id: str) -> ProvisioningTask:
        """
        Execute a provisioning task immediately.

        Processes all steps in sequence.
        """
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        task.status = ProvisioningStatus.IN_PROGRESS
        task.started_at = datetime.now()
        self._trigger_callbacks("on_task_start", task)

        logger.info(f"Executing task {task_id}: {task.description}")

        try:
            for step in task.steps:
                await self._execute_step(task, step)

            # Determine final status
            task.calculate_progress()

            if task.failed_steps == 0:
                task.status = ProvisioningStatus.COMPLETED
            elif task.completed_steps > 0:
                task.status = ProvisioningStatus.PARTIALLY_COMPLETED
            else:
                task.status = ProvisioningStatus.FAILED

            task.completed_at = datetime.now()

            self._trigger_callbacks("on_task_complete", task)
            logger.info(f"Task {task_id} completed with status: {task.status.value}")

        except Exception as e:
            task.status = ProvisioningStatus.FAILED
            task.error_summary = str(e)
            task.completed_at = datetime.now()

            self._trigger_callbacks("on_error", task, e)
            logger.error(f"Task {task_id} failed: {e}")

        return task

    async def _execute_step(self, task: ProvisioningTask, step: ProvisioningStep):
        """Execute a single provisioning step"""
        step.status = ProvisioningStatus.IN_PROGRESS
        step.started_at = datetime.now()

        try:
            # Get the connector for this system
            connector = await self.connector_factory.get_connector(step.target_system)
            if not connector:
                raise ValueError(f"Connector not found: {step.target_system}")

            # Ensure connected
            if not connector.is_connected:
                await connector.connect()

            # Execute the action
            result = await self._execute_action(connector, step)

            step.status = ProvisioningStatus.COMPLETED
            step.result = result.data if result.success else None
            step.completed_at = datetime.now()

            if not result.success:
                raise Exception(result.error or "Operation failed")

            self._trigger_callbacks("on_step_complete", task, step)
            logger.info(f"Step {step.step_id} completed: {step.action.value} on {step.target_system}")

        except Exception as e:
            step.error_message = str(e)
            step.retry_count += 1

            if step.retry_count < step.max_retries:
                step.status = ProvisioningStatus.RETRY_SCHEDULED
                logger.warning(f"Step {step.step_id} failed (attempt {step.retry_count}): {e}. Retrying...")

                # Retry with backoff
                await asyncio.sleep(step.retry_count * 2)
                await self._execute_step(task, step)
            else:
                step.status = ProvisioningStatus.FAILED
                step.completed_at = datetime.now()
                logger.error(f"Step {step.step_id} failed after {step.max_retries} attempts: {e}")

    async def _execute_action(self, connector: BaseConnector, step: ProvisioningStep):
        """Execute the specific action on the connector"""
        action = step.action
        params = step.parameters

        if action == ProvisioningAction.CREATE_USER:
            return await connector.create_user(params.get("user_data", {}))

        elif action == ProvisioningAction.UPDATE_USER:
            return await connector.update_user(step.target_user, params.get("user_data", {}))

        elif action == ProvisioningAction.DELETE_USER:
            return await connector.delete_user(step.target_user)

        elif action == ProvisioningAction.LOCK_USER:
            return await connector.lock_user(step.target_user)

        elif action == ProvisioningAction.UNLOCK_USER:
            return await connector.unlock_user(step.target_user)

        elif action == ProvisioningAction.RESET_PASSWORD:
            return await connector.reset_password(
                step.target_user,
                params.get("new_password", "")
            )

        elif action == ProvisioningAction.ASSIGN_ROLE:
            return await connector.assign_role(
                step.target_user,
                params.get("role_name", ""),
                params.get("valid_from"),
                params.get("valid_to")
            )

        elif action == ProvisioningAction.REMOVE_ROLE:
            return await connector.remove_role(
                step.target_user,
                params.get("role_name", "")
            )

        else:
            raise ValueError(f"Unknown action: {action}")

    def get_task(self, task_id: str) -> Optional[ProvisioningTask]:
        """Get a task by ID"""
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        status: Optional[ProvisioningStatus] = None,
        user_id: Optional[str] = None,
        source_type: Optional[str] = None,
        limit: int = 100
    ) -> List[ProvisioningTask]:
        """List tasks with optional filters"""
        tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]
        if user_id:
            tasks = [t for t in tasks if t.user_id == user_id]
        if source_type:
            tasks = [t for t in tasks if t.source_type == source_type]

        # Sort by created_at descending
        tasks.sort(key=lambda t: t.created_at, reverse=True)

        return tasks[:limit]

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or in-progress task"""
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.status in (ProvisioningStatus.PENDING, ProvisioningStatus.IN_PROGRESS):
            task.status = ProvisioningStatus.CANCELLED
            task.completed_at = datetime.now()

            # Cancel pending steps
            for step in task.steps:
                if step.status == ProvisioningStatus.PENDING:
                    step.status = ProvisioningStatus.CANCELLED

            logger.info(f"Cancelled task: {task_id}")
            return True

        return False

    # =========================================================================
    # Convenience Methods for Common Operations
    # =========================================================================

    async def provision_user(
        self,
        user_id: str,
        user_data: Dict,
        target_systems: List[str],
        source_type: str = "manual",
        source_id: str = ""
    ) -> ProvisioningTask:
        """
        Provision a new user across multiple systems.

        Creates user accounts in all specified systems.
        """
        task = ProvisioningTask(
            source_type=source_type,
            source_id=source_id,
            user_id=user_id,
            user_name=f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}",
            description=f"Create user {user_id} in {len(target_systems)} systems"
        )

        for system in target_systems:
            step = ProvisioningStep(
                action=ProvisioningAction.CREATE_USER,
                target_system=system,
                target_user=user_id,
                parameters={"user_data": {**user_data, "user_id": user_id}}
            )
            task.add_step(step)

        await self.submit_task(task)
        return await self.execute_task(task.task_id)

    async def assign_roles(
        self,
        user_id: str,
        roles: List[Dict],  # [{system, role_name, valid_from?, valid_to?}]
        source_type: str = "access_request",
        source_id: str = ""
    ) -> ProvisioningTask:
        """
        Assign multiple roles to a user.
        """
        task = ProvisioningTask(
            source_type=source_type,
            source_id=source_id,
            user_id=user_id,
            description=f"Assign {len(roles)} roles to user {user_id}"
        )

        for role in roles:
            step = ProvisioningStep(
                action=ProvisioningAction.ASSIGN_ROLE,
                target_system=role.get("system", ""),
                target_user=user_id,
                parameters={
                    "role_name": role.get("role_name", ""),
                    "valid_from": role.get("valid_from"),
                    "valid_to": role.get("valid_to")
                }
            )
            task.add_step(step)

        await self.submit_task(task)
        return await self.execute_task(task.task_id)

    async def revoke_roles(
        self,
        user_id: str,
        roles: List[Dict],  # [{system, role_name}]
        source_type: str = "access_request",
        source_id: str = ""
    ) -> ProvisioningTask:
        """
        Revoke multiple roles from a user.
        """
        task = ProvisioningTask(
            source_type=source_type,
            source_id=source_id,
            user_id=user_id,
            description=f"Revoke {len(roles)} roles from user {user_id}"
        )

        for role in roles:
            step = ProvisioningStep(
                action=ProvisioningAction.REMOVE_ROLE,
                target_system=role.get("system", ""),
                target_user=user_id,
                parameters={"role_name": role.get("role_name", "")}
            )
            task.add_step(step)

        await self.submit_task(task)
        return await self.execute_task(task.task_id)

    async def deprovision_user(
        self,
        user_id: str,
        target_systems: List[str],
        action: str = "lock",  # lock, disable, delete
        source_type: str = "jml_event",
        source_id: str = ""
    ) -> ProvisioningTask:
        """
        Deprovision a user from multiple systems.

        Can lock, disable, or delete user accounts.
        """
        action_map = {
            "lock": ProvisioningAction.LOCK_USER,
            "disable": ProvisioningAction.LOCK_USER,  # Most systems use lock for disable
            "delete": ProvisioningAction.DELETE_USER
        }
        prov_action = action_map.get(action, ProvisioningAction.LOCK_USER)

        task = ProvisioningTask(
            source_type=source_type,
            source_id=source_id,
            user_id=user_id,
            description=f"{action.capitalize()} user {user_id} in {len(target_systems)} systems"
        )

        for system in target_systems:
            step = ProvisioningStep(
                action=prov_action,
                target_system=system,
                target_user=user_id,
                parameters={}
            )
            task.add_step(step)

        await self.submit_task(task)
        return await self.execute_task(task.task_id)


# Global engine instance
provisioning_engine = ProvisioningEngine(connector_factory)
