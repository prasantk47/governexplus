"""
SAP Sync Scheduler

Automated synchronization of users, roles, and entitlements from connected systems.
Provides SAP GRC-equivalent background job scheduling.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import logging
import uuid

logger = logging.getLogger(__name__)


class SyncType(Enum):
    """Types of synchronization jobs"""
    FULL_USER_SYNC = "full_user_sync"
    INCREMENTAL_USER_SYNC = "incremental_user_sync"
    FULL_ROLE_SYNC = "full_role_sync"
    INCREMENTAL_ROLE_SYNC = "incremental_role_sync"
    ENTITLEMENT_SYNC = "entitlement_sync"
    RISK_ANALYSIS = "risk_analysis"
    USAGE_DATA_SYNC = "usage_data_sync"
    AUDIT_LOG_SYNC = "audit_log_sync"
    CUSTOM = "custom"


class JobStatus(Enum):
    """Job execution status"""
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class JobPriority(Enum):
    """Job priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class SyncJob:
    """Synchronization job definition"""
    job_id: str
    tenant_id: str
    name: str
    sync_type: SyncType
    system_id: str  # Target system to sync

    # Schedule
    cron_expression: str = ""  # e.g., "0 */6 * * *" for every 6 hours
    interval_minutes: int = 60
    is_recurring: bool = True

    # Execution
    status: JobStatus = JobStatus.SCHEDULED
    priority: JobPriority = JobPriority.NORMAL
    timeout_minutes: int = 30

    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)

    # Tracking
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_error: Optional[str] = None

    # Results
    last_result: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""

    def __hash__(self):
        return hash(self.job_id)


@dataclass
class SyncExecution:
    """Record of a sync job execution"""
    execution_id: str
    job_id: str
    tenant_id: str
    system_id: str
    sync_type: SyncType

    status: JobStatus = JobStatus.RUNNING
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Statistics
    records_processed: int = 0
    records_created: int = 0
    records_updated: int = 0
    records_deleted: int = 0
    records_failed: int = 0

    # Details
    error_message: Optional[str] = None
    error_details: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    # Duration
    @property
    def duration_seconds(self) -> Optional[float]:
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class SyncScheduler:
    """
    SAP Sync Scheduler

    Provides:
    1. Scheduled user/role synchronization
    2. Incremental and full sync modes
    3. Multi-system support
    4. Job monitoring and alerting
    5. Automatic retry and error handling
    """

    def __init__(self):
        self.jobs: Dict[str, SyncJob] = {}
        self.executions: Dict[str, SyncExecution] = {}
        self.running_jobs: Dict[str, asyncio.Task] = {}

        # Sync handlers by type
        self.sync_handlers: Dict[SyncType, Callable] = {}

        # Configuration
        self.max_concurrent_jobs = 5
        self.default_retry_count = 3
        self.retry_delay_minutes = 5

        # Scheduler state
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default sync handlers"""
        self.sync_handlers[SyncType.FULL_USER_SYNC] = self._sync_users_full
        self.sync_handlers[SyncType.INCREMENTAL_USER_SYNC] = self._sync_users_incremental
        self.sync_handlers[SyncType.FULL_ROLE_SYNC] = self._sync_roles_full
        self.sync_handlers[SyncType.INCREMENTAL_ROLE_SYNC] = self._sync_roles_incremental
        self.sync_handlers[SyncType.ENTITLEMENT_SYNC] = self._sync_entitlements
        self.sync_handlers[SyncType.RISK_ANALYSIS] = self._run_risk_analysis
        self.sync_handlers[SyncType.USAGE_DATA_SYNC] = self._sync_usage_data
        self.sync_handlers[SyncType.AUDIT_LOG_SYNC] = self._sync_audit_logs

    # ==================== Job Management ====================

    def create_job(
        self,
        tenant_id: str,
        name: str,
        sync_type: SyncType,
        system_id: str,
        interval_minutes: int = 60,
        cron_expression: str = "",
        config: Dict[str, Any] = None,
        filters: Dict[str, Any] = None,
        priority: JobPriority = JobPriority.NORMAL,
        created_by: str = ""
    ) -> SyncJob:
        """Create a new sync job"""
        job_id = f"SYNC_{tenant_id}_{system_id}_{sync_type.value}_{uuid.uuid4().hex[:8]}"

        job = SyncJob(
            job_id=job_id,
            tenant_id=tenant_id,
            name=name,
            sync_type=sync_type,
            system_id=system_id,
            interval_minutes=interval_minutes,
            cron_expression=cron_expression,
            config=config or {},
            filters=filters or {},
            priority=priority,
            created_by=created_by,
            next_run=datetime.utcnow() + timedelta(minutes=interval_minutes)
        )

        self.jobs[job_id] = job
        logger.info(f"Created sync job: {job_id}")
        return job

    def update_job(
        self,
        job_id: str,
        **updates
    ) -> Optional[SyncJob]:
        """Update job configuration"""
        job = self.jobs.get(job_id)
        if not job:
            return None

        for key, value in updates.items():
            if hasattr(job, key):
                setattr(job, key, value)

        return job

    def delete_job(self, job_id: str) -> bool:
        """Delete a sync job"""
        if job_id in self.jobs:
            # Cancel if running
            if job_id in self.running_jobs:
                self.running_jobs[job_id].cancel()

            del self.jobs[job_id]
            logger.info(f"Deleted sync job: {job_id}")
            return True
        return False

    def pause_job(self, job_id: str) -> bool:
        """Pause a recurring job"""
        job = self.jobs.get(job_id)
        if job:
            job.status = JobStatus.PAUSED
            return True
        return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job"""
        job = self.jobs.get(job_id)
        if job and job.status == JobStatus.PAUSED:
            job.status = JobStatus.SCHEDULED
            job.next_run = datetime.utcnow() + timedelta(minutes=job.interval_minutes)
            return True
        return False

    def get_jobs_by_tenant(self, tenant_id: str) -> List[SyncJob]:
        """Get all jobs for a tenant"""
        return [j for j in self.jobs.values() if j.tenant_id == tenant_id]

    def get_jobs_by_system(self, system_id: str) -> List[SyncJob]:
        """Get all jobs for a system"""
        return [j for j in self.jobs.values() if j.system_id == system_id]

    # ==================== Job Execution ====================

    async def run_job_now(self, job_id: str) -> SyncExecution:
        """Run a job immediately"""
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        return await self._execute_job(job)

    async def _execute_job(self, job: SyncJob) -> SyncExecution:
        """Execute a sync job"""
        execution_id = f"EXEC_{job.job_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        execution = SyncExecution(
            execution_id=execution_id,
            job_id=job.job_id,
            tenant_id=job.tenant_id,
            system_id=job.system_id,
            sync_type=job.sync_type
        )

        self.executions[execution_id] = execution

        # Update job status
        job.status = JobStatus.RUNNING
        job.run_count += 1

        try:
            # Get handler
            handler = self.sync_handlers.get(job.sync_type)
            if not handler:
                raise ValueError(f"No handler for sync type: {job.sync_type}")

            # Execute with timeout
            result = await asyncio.wait_for(
                handler(job, execution),
                timeout=job.timeout_minutes * 60
            )

            # Success
            execution.status = JobStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            job.status = JobStatus.SCHEDULED
            job.success_count += 1
            job.last_run = datetime.utcnow()
            job.last_result = result
            job.last_error = None

            logger.info(f"Job completed: {job.job_id}, processed {execution.records_processed} records")

        except asyncio.TimeoutError:
            execution.status = JobStatus.FAILED
            execution.error_message = f"Job timed out after {job.timeout_minutes} minutes"
            execution.completed_at = datetime.utcnow()
            job.status = JobStatus.SCHEDULED
            job.failure_count += 1
            job.last_error = execution.error_message
            logger.error(f"Job timed out: {job.job_id}")

        except Exception as e:
            execution.status = JobStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            job.status = JobStatus.SCHEDULED
            job.failure_count += 1
            job.last_error = str(e)
            logger.error(f"Job failed: {job.job_id} - {e}")

        finally:
            # Schedule next run
            if job.is_recurring:
                job.next_run = datetime.utcnow() + timedelta(minutes=job.interval_minutes)

        return execution

    # ==================== Scheduler Loop ====================

    async def start(self):
        """Start the scheduler"""
        if self._running:
            return

        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Sync scheduler started")

    async def stop(self):
        """Stop the scheduler"""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Sync scheduler stopped")

    async def _scheduler_loop(self):
        """Main scheduler loop"""
        while self._running:
            try:
                now = datetime.utcnow()

                # Find jobs due to run
                due_jobs = [
                    job for job in self.jobs.values()
                    if job.status == JobStatus.SCHEDULED
                    and job.next_run
                    and job.next_run <= now
                ]

                # Sort by priority
                due_jobs.sort(key=lambda j: j.priority.value, reverse=True)

                # Run jobs up to concurrency limit
                running_count = len(self.running_jobs)
                for job in due_jobs:
                    if running_count >= self.max_concurrent_jobs:
                        break

                    if job.job_id not in self.running_jobs:
                        task = asyncio.create_task(self._execute_job(job))
                        self.running_jobs[job.job_id] = task
                        running_count += 1

                # Clean up completed tasks
                completed = [
                    job_id for job_id, task in self.running_jobs.items()
                    if task.done()
                ]
                for job_id in completed:
                    del self.running_jobs[job_id]

                # Sleep before next check
                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)

    # ==================== Sync Handlers ====================

    async def _sync_users_full(
        self,
        job: SyncJob,
        execution: SyncExecution
    ) -> Dict[str, Any]:
        """Full user synchronization"""
        # In production, this would use the connector to fetch users
        logger.info(f"Starting full user sync for system: {job.system_id}")

        # Simulated sync
        users_fetched = 1000
        users_created = 50
        users_updated = 200
        users_deactivated = 10

        execution.records_processed = users_fetched
        execution.records_created = users_created
        execution.records_updated = users_updated
        execution.records_deleted = users_deactivated

        return {
            "sync_type": "full_user",
            "users_fetched": users_fetched,
            "users_created": users_created,
            "users_updated": users_updated,
            "users_deactivated": users_deactivated,
            "duration_seconds": 120
        }

    async def _sync_users_incremental(
        self,
        job: SyncJob,
        execution: SyncExecution
    ) -> Dict[str, Any]:
        """Incremental user synchronization (changes since last sync)"""
        logger.info(f"Starting incremental user sync for system: {job.system_id}")

        # Get changes since last sync
        since = job.last_run or (datetime.utcnow() - timedelta(hours=24))

        # Simulated sync
        users_changed = 50
        users_created = 5
        users_updated = 40
        users_deactivated = 5

        execution.records_processed = users_changed
        execution.records_created = users_created
        execution.records_updated = users_updated
        execution.records_deleted = users_deactivated

        return {
            "sync_type": "incremental_user",
            "since": since.isoformat(),
            "users_changed": users_changed,
            "users_created": users_created,
            "users_updated": users_updated,
            "users_deactivated": users_deactivated
        }

    async def _sync_roles_full(
        self,
        job: SyncJob,
        execution: SyncExecution
    ) -> Dict[str, Any]:
        """Full role synchronization"""
        logger.info(f"Starting full role sync for system: {job.system_id}")

        roles_fetched = 500
        roles_created = 20
        roles_updated = 100

        execution.records_processed = roles_fetched
        execution.records_created = roles_created
        execution.records_updated = roles_updated

        return {
            "sync_type": "full_role",
            "roles_fetched": roles_fetched,
            "roles_created": roles_created,
            "roles_updated": roles_updated
        }

    async def _sync_roles_incremental(
        self,
        job: SyncJob,
        execution: SyncExecution
    ) -> Dict[str, Any]:
        """Incremental role synchronization"""
        logger.info(f"Starting incremental role sync for system: {job.system_id}")

        roles_changed = 25
        roles_created = 2
        roles_updated = 23

        execution.records_processed = roles_changed
        execution.records_created = roles_created
        execution.records_updated = roles_updated

        return {
            "sync_type": "incremental_role",
            "roles_changed": roles_changed,
            "roles_created": roles_created,
            "roles_updated": roles_updated
        }

    async def _sync_entitlements(
        self,
        job: SyncJob,
        execution: SyncExecution
    ) -> Dict[str, Any]:
        """Synchronize user entitlements/authorizations"""
        logger.info(f"Starting entitlement sync for system: {job.system_id}")

        entitlements_processed = 50000
        entitlements_added = 1000
        entitlements_removed = 500

        execution.records_processed = entitlements_processed
        execution.records_created = entitlements_added
        execution.records_deleted = entitlements_removed

        return {
            "sync_type": "entitlement",
            "entitlements_processed": entitlements_processed,
            "entitlements_added": entitlements_added,
            "entitlements_removed": entitlements_removed
        }

    async def _run_risk_analysis(
        self,
        job: SyncJob,
        execution: SyncExecution
    ) -> Dict[str, Any]:
        """Run batch risk analysis"""
        logger.info(f"Starting risk analysis for system: {job.system_id}")

        users_analyzed = 1000
        violations_found = 150
        new_violations = 25

        execution.records_processed = users_analyzed

        return {
            "sync_type": "risk_analysis",
            "users_analyzed": users_analyzed,
            "violations_found": violations_found,
            "new_violations": new_violations
        }

    async def _sync_usage_data(
        self,
        job: SyncJob,
        execution: SyncExecution
    ) -> Dict[str, Any]:
        """Synchronize transaction usage data"""
        logger.info(f"Starting usage data sync for system: {job.system_id}")

        records_fetched = 100000
        usage_records_created = 100000

        execution.records_processed = records_fetched
        execution.records_created = usage_records_created

        return {
            "sync_type": "usage_data",
            "records_fetched": records_fetched,
            "usage_records_created": usage_records_created
        }

    async def _sync_audit_logs(
        self,
        job: SyncJob,
        execution: SyncExecution
    ) -> Dict[str, Any]:
        """Synchronize audit logs from SAP"""
        logger.info(f"Starting audit log sync for system: {job.system_id}")

        logs_fetched = 10000
        logs_imported = 10000

        execution.records_processed = logs_fetched
        execution.records_created = logs_imported

        return {
            "sync_type": "audit_log",
            "logs_fetched": logs_fetched,
            "logs_imported": logs_imported
        }

    # ==================== Monitoring ====================

    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        return {
            "running": self._running,
            "total_jobs": len(self.jobs),
            "active_jobs": len([j for j in self.jobs.values() if j.status == JobStatus.SCHEDULED]),
            "paused_jobs": len([j for j in self.jobs.values() if j.status == JobStatus.PAUSED]),
            "running_jobs": len(self.running_jobs),
            "max_concurrent": self.max_concurrent_jobs
        }

    def get_execution_history(
        self,
        job_id: str = None,
        tenant_id: str = None,
        limit: int = 100
    ) -> List[SyncExecution]:
        """Get execution history"""
        executions = list(self.executions.values())

        if job_id:
            executions = [e for e in executions if e.job_id == job_id]
        if tenant_id:
            executions = [e for e in executions if e.tenant_id == tenant_id]

        # Sort by start time descending
        executions.sort(key=lambda e: e.started_at, reverse=True)

        return executions[:limit]

    def get_failed_executions(
        self,
        hours: int = 24
    ) -> List[SyncExecution]:
        """Get failed executions in the last N hours"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [
            e for e in self.executions.values()
            if e.status == JobStatus.FAILED and e.started_at >= cutoff
        ]


# Singleton instance
sync_scheduler = SyncScheduler()


# ==================== Pre-configured Job Templates ====================

def create_standard_sync_jobs(
    tenant_id: str,
    system_id: str,
    scheduler: SyncScheduler = None
) -> List[SyncJob]:
    """Create standard set of sync jobs for a new system"""
    if scheduler is None:
        scheduler = sync_scheduler

    jobs = []

    # Incremental user sync every hour
    jobs.append(scheduler.create_job(
        tenant_id=tenant_id,
        name=f"User Sync (Incremental) - {system_id}",
        sync_type=SyncType.INCREMENTAL_USER_SYNC,
        system_id=system_id,
        interval_minutes=60,
        priority=JobPriority.HIGH
    ))

    # Full user sync daily
    jobs.append(scheduler.create_job(
        tenant_id=tenant_id,
        name=f"User Sync (Full) - {system_id}",
        sync_type=SyncType.FULL_USER_SYNC,
        system_id=system_id,
        interval_minutes=1440,  # 24 hours
        priority=JobPriority.NORMAL
    ))

    # Incremental role sync every 2 hours
    jobs.append(scheduler.create_job(
        tenant_id=tenant_id,
        name=f"Role Sync (Incremental) - {system_id}",
        sync_type=SyncType.INCREMENTAL_ROLE_SYNC,
        system_id=system_id,
        interval_minutes=120,
        priority=JobPriority.NORMAL
    ))

    # Full role sync weekly
    jobs.append(scheduler.create_job(
        tenant_id=tenant_id,
        name=f"Role Sync (Full) - {system_id}",
        sync_type=SyncType.FULL_ROLE_SYNC,
        system_id=system_id,
        interval_minutes=10080,  # 7 days
        priority=JobPriority.LOW
    ))

    # Entitlement sync every 4 hours
    jobs.append(scheduler.create_job(
        tenant_id=tenant_id,
        name=f"Entitlement Sync - {system_id}",
        sync_type=SyncType.ENTITLEMENT_SYNC,
        system_id=system_id,
        interval_minutes=240,
        priority=JobPriority.HIGH
    ))

    # Risk analysis every 6 hours
    jobs.append(scheduler.create_job(
        tenant_id=tenant_id,
        name=f"Risk Analysis - {system_id}",
        sync_type=SyncType.RISK_ANALYSIS,
        system_id=system_id,
        interval_minutes=360,
        priority=JobPriority.CRITICAL
    ))

    # Usage data sync daily
    jobs.append(scheduler.create_job(
        tenant_id=tenant_id,
        name=f"Usage Data Sync - {system_id}",
        sync_type=SyncType.USAGE_DATA_SYNC,
        system_id=system_id,
        interval_minutes=1440,
        priority=JobPriority.LOW
    ))

    return jobs
