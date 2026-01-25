"""
Provisioning Queue

Asynchronous queue for processing provisioning tasks.
Supports priority-based processing, retry handling, and persistence.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import logging
import asyncio
import heapq
import uuid

from .engine import ProvisioningTask, ProvisioningStatus, provisioning_engine

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = 1   # Emergency access, security incidents
    HIGH = 3       # Urgent business requests
    NORMAL = 5     # Standard access requests
    LOW = 7        # Batch operations, scheduled tasks
    BACKGROUND = 9 # Cleanup, optimization


@dataclass(order=True)
class QueuedTask:
    """A task in the provisioning queue"""
    priority: int
    scheduled_time: datetime = field(compare=True)
    task_id: str = field(compare=False)
    task: ProvisioningTask = field(compare=False)

    # Queue metadata
    queued_at: datetime = field(default_factory=datetime.now, compare=False)
    attempt: int = field(default=0, compare=False)
    max_attempts: int = field(default=3, compare=False)
    last_error: Optional[str] = field(default=None, compare=False)

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "priority": self.priority,
            "scheduled_time": self.scheduled_time.isoformat(),
            "queued_at": self.queued_at.isoformat(),
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "task_status": self.task.status.value,
            "last_error": self.last_error
        }


class ProvisioningQueue:
    """
    Priority queue for provisioning tasks.

    Features:
    - Priority-based processing
    - Scheduled execution
    - Retry with exponential backoff
    - Concurrent workers
    - Persistence support
    """

    def __init__(
        self,
        max_workers: int = 5,
        max_queue_size: int = 10000
    ):
        self._queue: List[QueuedTask] = []
        self._processing: Dict[str, QueuedTask] = {}
        self._completed: Dict[str, QueuedTask] = {}
        self._failed: Dict[str, QueuedTask] = {}

        self.max_workers = max_workers
        self.max_queue_size = max_queue_size

        self._running = False
        self._workers: List[asyncio.Task] = []
        self._lock = asyncio.Lock()
        self._condition = asyncio.Condition()

        # Statistics
        self._stats = {
            "total_queued": 0,
            "total_processed": 0,
            "total_failed": 0,
            "total_retried": 0
        }

        # Callbacks
        self._callbacks: Dict[str, List[Callable]] = {
            "on_task_queued": [],
            "on_task_started": [],
            "on_task_completed": [],
            "on_task_failed": [],
            "on_task_retried": []
        }

    def register_callback(self, event: str, callback: Callable):
        """Register a callback for queue events"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    async def _trigger_callbacks(self, event: str, *args, **kwargs):
        """Trigger registered callbacks"""
        for callback in self._callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args, **kwargs)
                else:
                    callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")

    async def enqueue(
        self,
        task: ProvisioningTask,
        priority: TaskPriority = TaskPriority.NORMAL,
        scheduled_time: Optional[datetime] = None
    ) -> str:
        """
        Add a task to the queue.

        Args:
            task: The provisioning task
            priority: Task priority level
            scheduled_time: When to execute (None = immediately)

        Returns:
            Task ID
        """
        async with self._lock:
            if len(self._queue) >= self.max_queue_size:
                raise ValueError("Queue is full")

            queued = QueuedTask(
                priority=priority.value,
                scheduled_time=scheduled_time or datetime.now(),
                task_id=task.task_id,
                task=task
            )

            heapq.heappush(self._queue, queued)
            self._stats["total_queued"] += 1

        async with self._condition:
            self._condition.notify()

        await self._trigger_callbacks("on_task_queued", queued)
        logger.info(f"Queued task {task.task_id} with priority {priority.name}")

        return task.task_id

    async def start(self):
        """Start the queue processing workers"""
        if self._running:
            return

        self._running = True
        logger.info(f"Starting provisioning queue with {self.max_workers} workers")

        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)

    async def stop(self, wait: bool = True):
        """Stop the queue processing"""
        self._running = False

        async with self._condition:
            self._condition.notify_all()

        if wait:
            await asyncio.gather(*self._workers, return_exceptions=True)

        self._workers.clear()
        logger.info("Provisioning queue stopped")

    async def _worker(self, worker_id: int):
        """Worker coroutine that processes tasks from the queue"""
        logger.info(f"Worker {worker_id} started")

        while self._running:
            try:
                queued = await self._get_next_task()
                if not queued:
                    continue

                await self._process_task(worker_id, queued)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)

        logger.info(f"Worker {worker_id} stopped")

    async def _get_next_task(self) -> Optional[QueuedTask]:
        """Get the next task from the queue"""
        async with self._condition:
            while self._running:
                async with self._lock:
                    if not self._queue:
                        pass
                    else:
                        # Check if next task is scheduled
                        next_task = self._queue[0]
                        if next_task.scheduled_time <= datetime.now():
                            return heapq.heappop(self._queue)

                # Wait for notification or timeout
                try:
                    await asyncio.wait_for(
                        self._condition.wait(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    pass

        return None

    async def _process_task(self, worker_id: int, queued: QueuedTask):
        """Process a single task"""
        task = queued.task
        task_id = queued.task_id

        logger.info(f"Worker {worker_id} processing task {task_id}")

        async with self._lock:
            self._processing[task_id] = queued

        await self._trigger_callbacks("on_task_started", queued)

        try:
            # Execute the task
            result = await provisioning_engine.execute_task(task_id)

            if result.status == ProvisioningStatus.COMPLETED:
                async with self._lock:
                    self._processing.pop(task_id, None)
                    self._completed[task_id] = queued
                    self._stats["total_processed"] += 1

                await self._trigger_callbacks("on_task_completed", queued)
                logger.info(f"Task {task_id} completed successfully")

            elif result.status == ProvisioningStatus.PARTIALLY_COMPLETED:
                # Handle partial completion based on business rules
                async with self._lock:
                    self._processing.pop(task_id, None)
                    self._completed[task_id] = queued
                    self._stats["total_processed"] += 1

                await self._trigger_callbacks("on_task_completed", queued)
                logger.warning(f"Task {task_id} partially completed")

            else:
                raise Exception(result.error_summary or "Task failed")

        except Exception as e:
            await self._handle_failure(queued, str(e))

    async def _handle_failure(self, queued: QueuedTask, error: str):
        """Handle task failure with retry logic"""
        task_id = queued.task_id
        queued.attempt += 1
        queued.last_error = error

        async with self._lock:
            self._processing.pop(task_id, None)

        if queued.attempt < queued.max_attempts:
            # Schedule retry with exponential backoff
            delay = min(300, 2 ** queued.attempt * 10)  # Max 5 minutes
            queued.scheduled_time = datetime.now() + timedelta(seconds=delay)
            queued.task.status = ProvisioningStatus.RETRY_SCHEDULED

            async with self._lock:
                heapq.heappush(self._queue, queued)
                self._stats["total_retried"] += 1

            await self._trigger_callbacks("on_task_retried", queued)
            logger.warning(f"Task {task_id} scheduled for retry in {delay}s (attempt {queued.attempt})")

        else:
            # Max retries exceeded
            async with self._lock:
                self._failed[task_id] = queued
                self._stats["total_failed"] += 1

            await self._trigger_callbacks("on_task_failed", queued)
            logger.error(f"Task {task_id} failed after {queued.max_attempts} attempts: {error}")

    def get_status(self) -> Dict:
        """Get queue status"""
        return {
            "running": self._running,
            "workers": len(self._workers),
            "queue_size": len(self._queue),
            "processing": len(self._processing),
            "completed": len(self._completed),
            "failed": len(self._failed),
            "stats": self._stats.copy()
        }

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get status of a specific task"""
        for store in [self._processing, self._completed, self._failed]:
            if task_id in store:
                return store[task_id].to_dict()

        # Check queue
        for queued in self._queue:
            if queued.task_id == task_id:
                return queued.to_dict()

        return None

    def list_queued(self, limit: int = 100) -> List[Dict]:
        """List queued tasks"""
        return [q.to_dict() for q in sorted(self._queue)[:limit]]

    def list_processing(self) -> List[Dict]:
        """List currently processing tasks"""
        return [q.to_dict() for q in self._processing.values()]

    def list_completed(self, limit: int = 100) -> List[Dict]:
        """List recently completed tasks"""
        completed = list(self._completed.values())
        completed.sort(key=lambda x: x.task.completed_at or x.queued_at, reverse=True)
        return [q.to_dict() for q in completed[:limit]]

    def list_failed(self, limit: int = 100) -> List[Dict]:
        """List failed tasks"""
        failed = list(self._failed.values())
        failed.sort(key=lambda x: x.queued_at, reverse=True)
        return [q.to_dict() for q in failed[:limit]]

    async def retry_failed(self, task_id: str) -> bool:
        """Manually retry a failed task"""
        async with self._lock:
            queued = self._failed.pop(task_id, None)

        if not queued:
            return False

        queued.attempt = 0
        queued.scheduled_time = datetime.now()
        queued.task.status = ProvisioningStatus.PENDING

        await self.enqueue(queued.task, TaskPriority(queued.priority))
        return True

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a queued task"""
        async with self._lock:
            for i, queued in enumerate(self._queue):
                if queued.task_id == task_id:
                    self._queue.pop(i)
                    heapq.heapify(self._queue)
                    queued.task.status = ProvisioningStatus.CANCELLED
                    return True

        return False


# Global queue instance
provisioning_queue = ProvisioningQueue()
