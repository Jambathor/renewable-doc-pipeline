"""
Background task runner for in-process async processing.

This module provides background task execution for the renewable energy PDF processing
pipeline. It handles document processing jobs asynchronously within the same process
as the main application, eliminating the need for external message queues in demo mode.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import UUID, uuid4
from enum import Enum
from dataclasses import dataclass, field

from src.models.processing_job import ProcessingJob, JobStatus, ErrorType
from src.storage.postgres_client import get_postgres_client, DatabaseError

logger = logging.getLogger(__name__)


class TaskPriority(str, Enum):
    """Task priority levels for job scheduling."""
    
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class BackgroundTask:
    """Represents a background task to be executed."""
    
    task_id: str = field(default_factory=lambda: str(uuid4()))
    job_id: UUID = field(default_factory=uuid4)
    account_id: UUID = field(default_factory=uuid4)
    task_type: str = "unknown"
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = None
    attempts: int = 0
    max_attempts: int = 3
    task_func: Optional[Callable] = None
    task_args: tuple = field(default_factory=tuple)
    task_kwargs: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None


class TaskRunnerError(Exception):
    """Base exception for task runner errors."""
    pass


class TaskExecutionError(TaskRunnerError):
    """Exception raised when task execution fails."""
    pass


class TaskSchedulingError(TaskRunnerError):
    """Exception raised when task scheduling fails."""
    pass


class BackgroundTaskRunner:
    """In-process background task runner for document processing jobs."""
    
    def __init__(self, max_concurrent_tasks: int = 5, poll_interval: float = 1.0):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.poll_interval = poll_interval
        self.running = False
        self.tasks: List[BackgroundTask] = []
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.completed_tasks: List[BackgroundTask] = []
        self.failed_tasks: List[BackgroundTask] = []
        self.stats = {
            "total_scheduled": 0,
            "total_completed": 0,
            "total_failed": 0,
            "current_active": 0
        }
        self.postgres_client = get_postgres_client()
    
    async def start(self) -> None:
        """Start the background task runner."""
        if self.running:
            logger.warning("Task runner is already running")
            return
        
        self.running = True
        logger.info("Starting background task runner", extra={
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "poll_interval": self.poll_interval
        })
        
        # Start the main task processing loop
        asyncio.create_task(self._process_tasks())
    
    async def stop(self) -> None:
        """Stop the background task runner and wait for active tasks to complete."""
        logger.info("Stopping background task runner")
        self.running = False
        
        # Wait for active tasks to complete (with timeout)
        if self.active_tasks:
            logger.info(f"Waiting for {len(self.active_tasks)} active tasks to complete")
            await asyncio.wait(self.active_tasks.values(), timeout=30.0)
        
        logger.info("Background task runner stopped")
    
    async def schedule_task(
        self,
        task_func: Callable,
        *args,
        job_id: Optional[UUID] = None,
        account_id: Optional[UUID] = None,
        task_type: str = "unknown",
        priority: TaskPriority = TaskPriority.MEDIUM,
        delay: float = 0.0,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """Schedule a background task for execution."""
        scheduled_at = datetime.utcnow()
        if delay > 0:
            scheduled_at = datetime.fromtimestamp(time.time() + delay)
        
        task = BackgroundTask(
            job_id=job_id or uuid4(),
            account_id=account_id or uuid4(),
            task_type=task_type,
            priority=priority,
            scheduled_at=scheduled_at,
            task_func=task_func,
            task_args=args,
            task_kwargs=kwargs,
            correlation_id=correlation_id
        )
        
        self.tasks.append(task)
        self.stats["total_scheduled"] += 1
        
        logger.info(f"Scheduled background task", extra={
            "task_id": task.task_id,
            "task_type": task_type,
            "priority": priority.value,
            "job_id": str(job_id),
            "correlation_id": correlation_id
        })
        
        return task.task_id
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a specific task."""
        # Check active tasks
        if task_id in self.active_tasks:
            return {"status": "running", "task_id": task_id}
        
        # Check pending tasks
        for task in self.tasks:
            if task.task_id == task_id:
                return {
                    "status": "pending", 
                    "task_id": task_id,
                    "scheduled_at": task.scheduled_at.isoformat() if task.scheduled_at else None,
                    "attempts": task.attempts
                }
        
        # Check completed tasks
        for task in self.completed_tasks:
            if task.task_id == task_id:
                return {"status": "completed", "task_id": task_id}
        
        # Check failed tasks
        for task in self.failed_tasks:
            if task.task_id == task_id:
                return {"status": "failed", "task_id": task_id, "attempts": task.attempts}
        
        return None
    
    async def get_runner_stats(self) -> Dict[str, Any]:
        """Get task runner statistics."""
        return {
            "running": self.running,
            "pending_tasks": len(self.tasks),
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "stats": self.stats.copy()
        }
    
    async def _process_tasks(self) -> None:
        """Main task processing loop."""
        while self.running:
            try:
                await self._execute_pending_tasks()
                await self._cleanup_completed_tasks()
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Error in task processing loop: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)
    
    async def _execute_pending_tasks(self) -> None:
        """Execute pending tasks up to the concurrency limit."""
        if len(self.active_tasks) >= self.max_concurrent_tasks:
            return
        
        # Sort tasks by priority and scheduled time
        self.tasks.sort(key=lambda t: (
            {"high": 0, "medium": 1, "low": 2}[t.priority.value],
            t.scheduled_at or datetime.utcnow()
        ))
        
        current_time = datetime.utcnow()
        tasks_to_execute = []
        
        for task in self.tasks[:]:
            if len(self.active_tasks) + len(tasks_to_execute) >= self.max_concurrent_tasks:
                break
            
            # Check if task is ready to execute
            if task.scheduled_at and task.scheduled_at > current_time:
                continue
            
            tasks_to_execute.append(task)
            self.tasks.remove(task)
        
        # Execute tasks
        for task in tasks_to_execute:
            asyncio_task = asyncio.create_task(self._execute_task(task))
            self.active_tasks[task.task_id] = asyncio_task
            self.stats["current_active"] = len(self.active_tasks)
    
    async def _execute_task(self, task: BackgroundTask) -> None:
        """Execute a single background task."""
        start_time = time.time()
        task.attempts += 1
        
        # Update job status to running if it's a processing job
        if task.task_type == "document_processing":
            await self._update_job_status(task.job_id, JobStatus.RUNNING, 0)
        
        logger.info(f"Executing background task", extra={
            "task_id": task.task_id,
            "task_type": task.task_type,
            "attempt": task.attempts,
            "correlation_id": task.correlation_id
        })
        
        try:
            if task.task_func:
                if asyncio.iscoroutinefunction(task.task_func):
                    await task.task_func(*task.task_args, **task.task_kwargs)
                else:
                    # Execute sync function in thread pool
                    await asyncio.get_event_loop().run_in_executor(
                        None, task.task_func, *task.task_args
                    )
            
            # Task completed successfully
            execution_time = time.time() - start_time
            logger.info(f"Background task completed", extra={
                "task_id": task.task_id,
                "execution_time": f"{execution_time:.2f}s",
                "correlation_id": task.correlation_id
            })
            
            self.completed_tasks.append(task)
            self.stats["total_completed"] += 1
            
            # Update job status to completed
            if task.task_type == "document_processing":
                await self._update_job_status(task.job_id, JobStatus.COMPLETED, 100)
        
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Background task failed", extra={
                "task_id": task.task_id,
                "error": str(e),
                "attempt": task.attempts,
                "execution_time": f"{execution_time:.2f}s",
                "correlation_id": task.correlation_id
            }, exc_info=True)
            
            # Determine if task should be retried
            if task.attempts < task.max_attempts:
                # Schedule retry with exponential backoff
                retry_delay = 2 ** (task.attempts - 1)  # 1s, 2s, 4s
                task.scheduled_at = datetime.fromtimestamp(time.time() + retry_delay)
                self.tasks.append(task)
                
                logger.info(f"Scheduling task retry", extra={
                    "task_id": task.task_id,
                    "retry_delay": retry_delay,
                    "attempt": task.attempts + 1
                })
                
                # Update job status to retrying
                if task.task_type == "document_processing":
                    await self._update_job_status(
                        task.job_id, JobStatus.RETRYING, 0, str(e), ErrorType.PROCESSING_ERROR
                    )
            else:
                # Task failed permanently
                self.failed_tasks.append(task)
                self.stats["total_failed"] += 1
                
                # Update job status to failed
                if task.task_type == "document_processing":
                    await self._update_job_status(
                        task.job_id, JobStatus.FAILED, 0, str(e), ErrorType.PROCESSING_ERROR
                    )
    
    async def _cleanup_completed_tasks(self) -> None:
        """Clean up completed async tasks."""
        completed_task_ids = []
        
        for task_id, asyncio_task in self.active_tasks.items():
            if asyncio_task.done():
                completed_task_ids.append(task_id)
        
        for task_id in completed_task_ids:
            del self.active_tasks[task_id]
        
        self.stats["current_active"] = len(self.active_tasks)
    
    async def _update_job_status(
        self,
        job_id: UUID,
        status: JobStatus,
        progress: int,
        error_message: Optional[str] = None,
        error_type: Optional[ErrorType] = None
    ) -> None:
        """Update processing job status in database."""
        try:
            update_data = {
                "status": status.value,
                "progress_percentage": progress
            }
            
            if status == JobStatus.COMPLETED:
                update_data["completed_at"] = datetime.utcnow()
            elif error_message:
                update_data["error_message"] = error_message
                if error_type:
                    update_data["error_type"] = error_type.value
            
            await self.postgres_client.update_record("processing_jobs", job_id, update_data)
            
        except DatabaseError as e:
            logger.error(f"Failed to update job status: {e}", extra={"job_id": str(job_id)})


# Global task runner instance
_task_runner: Optional[BackgroundTaskRunner] = None


def get_task_runner() -> BackgroundTaskRunner:
    """Get the global task runner instance."""
    global _task_runner
    if _task_runner is None:
        _task_runner = BackgroundTaskRunner()
    return _task_runner


async def schedule_document_processing(
    document_id: UUID,
    job_id: UUID,
    account_id: UUID,
    correlation_id: Optional[str] = None
) -> str:
    """Schedule a document processing task."""
    from src.services.document_service import process_document
    
    runner = get_task_runner()
    return await runner.schedule_task(
        process_document,
        document_id,
        job_id=job_id,
        account_id=account_id,
        task_type="document_processing",
        priority=TaskPriority.HIGH,
        correlation_id=correlation_id
    )


async def get_health_status() -> Dict[str, str]:
    """Get task runner health status for /healthz endpoint."""
    runner = get_task_runner()
    stats = await runner.get_runner_stats()
    
    # Determine health based on runner state
    if not stats["running"]:
        return {"queue": "unhealthy"}
    
    # Check if we have too many failed tasks
    failure_rate = stats["stats"]["total_failed"] / max(1, stats["stats"]["total_scheduled"])
    if failure_rate > 0.5:  # More than 50% failure rate
        return {"queue": "unhealthy"}
    
    return {"queue": "healthy"}