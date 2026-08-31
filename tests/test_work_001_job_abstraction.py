"""Unit and integration test suite for WORK-001 Job Abstraction.

Validates:
1. JobRecord, PipelineRun, JobState, and JobType schemas.
2. JobStateMachine deterministic state transition rules and terminal invariants.
3. InMemoryJobRepository indexing, retrieval, and idempotency lookups.
4. SyncJobRunner synchronous execution, retry accounting, and safe error capture.
5. Canonical domain handlers (ingest, event construction, enrich, classify).
6. Security and secret sanitization on job records, metadata, and error logs.
"""

from datetime import UTC, datetime
from typing import Any

import pytest

from packages.context.models import ContextFeature
from packages.errors.codes import ErrorCode
from packages.errors.exceptions import (
    InvalidJobStateTransitionError,
    MissingConfigurationError,
)
from packages.schemas.common import Coordinate
from packages.schemas.detection import Detection
from packages.schemas.enums import ContextType, DayNight
from packages.schemas.event import Event
from packages.schemas.job import (
    JobRecord,
    JobState,
    JobType,
    PipelineRun,
    PipelineRunStatus,
)
from services.worker.jobs.context import JobContext
from services.worker.jobs.handler import JobRegistry
from services.worker.jobs.handlers import (
    CallableJobHandler,
    ContextEnrichJobHandler,
    EndToEndPipelineJobHandler,
    EventConstructJobHandler,
    FIRMSIngestJobHandler,
    IntelligenceClassifyJobHandler,
)
from services.worker.jobs.repository import InMemoryJobRepository
from services.worker.jobs.runner import SyncJobRunner
from services.worker.jobs.state_machine import JobStateMachine


def _create_sample_detection(det_id: str, lat: float, lon: float) -> Detection:
    """Helper to construct a valid canonical Detection."""
    return Detection(
        detection_id=det_id,
        source="firms",
        source_snapshot_id="snap_test_001",
        acquired_at=datetime(2026, 8, 20, 10, 0, 0, tzinfo=UTC),
        geometry=Coordinate(latitude=lat, longitude=lon),
        satellite="SNPP",
        instrument="VIIRS",
        product_type="NRT",
        product_version="v1.0",
        raw_hash="hash_" + det_id,
        brightness_ti4_k=345.5,
        frp_mw=25.0,
        confidence="nominal",
        day_night=DayNight.DAY,
    )


# ==============================================================================
# 1. Domain Models & Schemas
# ==============================================================================


class TestJobSchemas:
    """Test suite for JobRecord and PipelineRun schemas."""

    def test_job_record_defaults(self) -> None:
        job = JobRecord(job_type=JobType.INGEST.value)
        assert job.job_id.startswith("job_")
        assert job.state == JobState.QUEUED
        assert job.attempt_count == 0
        assert job.max_attempts == 3
        assert job.started_at is None
        assert job.completed_at is None
        assert job.error_code is None
        assert job.error_message_safe is None
        assert isinstance(job.created_at, datetime)
        assert job.created_at.tzinfo is not None

    def test_pipeline_run_defaults(self) -> None:
        run = PipelineRun(pipeline_name="jamnagar_flaring_pipeline")
        assert run.pipeline_run_id.startswith("run_")
        assert run.status == PipelineRunStatus.QUEUED
        assert run.pipeline_version == "v1.0.0"
        assert run.input_snapshot_ids == []
        assert run.completed_at is None


# ==============================================================================
# 2. Pure State Machine
# ==============================================================================


class TestJobStateMachine:
    """Test suite for JobStateMachine transition invariants."""

    def test_valid_happy_path_transitions(self) -> None:
        job = JobRecord(job_type="test")
        assert job.state == JobState.QUEUED

        # QUEUED -> RUNNING
        running = JobStateMachine.transition(job, JobState.RUNNING)
        assert running.state == JobState.RUNNING
        assert running.attempt_count == 1
        assert running.started_at is not None
        assert running.completed_at is None

        # RUNNING -> SUCCEEDED
        succeeded = JobStateMachine.transition(
            running,
            JobState.SUCCEEDED,
            result_summary={"status": "ok", "items_processed": 42},
        )
        assert succeeded.state == JobState.SUCCEEDED
        assert succeeded.completed_at is not None
        assert succeeded.result_summary == {"status": "ok", "items_processed": 42}
        assert JobStateMachine.is_terminal_state(succeeded.state) is True

    def test_valid_failure_and_retry_transitions(self) -> None:
        job = JobRecord(job_type="test")

        # QUEUED -> RUNNING
        running = JobStateMachine.transition(job, JobState.RUNNING)
        assert running.attempt_count == 1

        # RUNNING -> FAILED
        failed = JobStateMachine.transition(
            running,
            JobState.FAILED,
            error_code=ErrorCode.DATABASE_ERROR.value,
            error_message_safe="Database timeout occurred",
        )
        assert failed.state == JobState.FAILED
        assert failed.error_code == ErrorCode.DATABASE_ERROR.value
        assert failed.error_message_safe == "Database timeout occurred"
        assert failed.completed_at is not None

        # FAILED -> QUEUED (Retry)
        retried = JobStateMachine.transition(failed, JobState.QUEUED)
        assert retried.state == JobState.QUEUED

        # QUEUED -> RUNNING (Second attempt)
        running_2 = JobStateMachine.transition(retried, JobState.RUNNING)
        assert running_2.attempt_count == 2

    def test_valid_blocked_transition(self) -> None:
        job = JobRecord(job_type="test")
        running = JobStateMachine.transition(job, JobState.RUNNING)

        # RUNNING -> BLOCKED
        blocked = JobStateMachine.transition(
            running,
            JobState.BLOCKED,
            error_code=ErrorCode.MISSING_CONFIGURATION.value,
            error_message_safe="Scientific parameter is unset",
        )
        assert blocked.state == JobState.BLOCKED
        assert blocked.error_code == ErrorCode.MISSING_CONFIGURATION.value

        # BLOCKED -> QUEUED
        unblocked = JobStateMachine.transition(blocked, JobState.QUEUED)
        assert unblocked.state == JobState.QUEUED

    def test_cancellation_transitions(self) -> None:
        # 1. Cancel while QUEUED
        job = JobRecord(job_type="test")
        cancelled_from_queued = JobStateMachine.transition(
            job, JobState.CANCELLED, error_message_safe="Cancelled by user"
        )
        assert cancelled_from_queued.state == JobState.CANCELLED
        assert JobStateMachine.is_terminal_state(cancelled_from_queued.state) is True

        # 2. Cancel while RUNNING via CANCEL_REQUESTED
        job2 = JobRecord(job_type="test")
        running2 = JobStateMachine.transition(job2, JobState.RUNNING)
        cancel_req = JobStateMachine.transition(running2, JobState.CANCEL_REQUESTED)
        assert cancel_req.state == JobState.CANCEL_REQUESTED

        cancelled_final = JobStateMachine.transition(cancel_req, JobState.CANCELLED)
        assert cancelled_final.state == JobState.CANCELLED

    def test_illegal_state_transitions_raise_error(self) -> None:
        job = JobRecord(job_type="test")
        running = JobStateMachine.transition(job, JobState.RUNNING)
        succeeded = JobStateMachine.transition(running, JobState.SUCCEEDED)

        # SUCCEEDED is terminal: cannot transition anywhere
        with pytest.raises(InvalidJobStateTransitionError):
            JobStateMachine.transition(succeeded, JobState.RUNNING)

        with pytest.raises(InvalidJobStateTransitionError):
            JobStateMachine.transition(succeeded, JobState.QUEUED)

        # Direct illegal transition QUEUED -> SUCCEEDED
        fresh_job = JobRecord(job_type="test")
        with pytest.raises(InvalidJobStateTransitionError):
            JobStateMachine.transition(fresh_job, JobState.SUCCEEDED)

    def test_state_history_audit_trail_in_metadata(self) -> None:
        job = JobRecord(job_type="test")
        running = JobStateMachine.transition(job, JobState.RUNNING)
        succeeded = JobStateMachine.transition(running, JobState.SUCCEEDED)

        history = succeeded.metadata.get("state_history", [])
        assert len(history) == 2
        assert history[0]["from_state"] == "QUEUED"
        assert history[0]["to_state"] == "RUNNING"
        assert history[1]["from_state"] == "RUNNING"
        assert history[1]["to_state"] == "SUCCEEDED"


# ==============================================================================
# 3. Repository & Idempotency
# ==============================================================================


class TestJobRepository:
    """Test suite for InMemoryJobRepository."""

    def test_save_get_and_idempotency_lookup(self) -> None:
        repo = InMemoryJobRepository()
        job = JobRecord(
            job_type="test_ingest",
            idempotency_key="firms:2026-08-20:jamnagar",
            input_reference={"bbox": [22.0, 69.0, 23.0, 70.0]},
        )
        repo.save_job(job)

        # Lookup by ID
        fetched = repo.get_job(job.job_id)
        assert fetched is not None
        assert fetched.job_id == job.job_id

        # Lookup by idempotency key
        by_key = repo.get_job_by_idempotency_key("firms:2026-08-20:jamnagar")
        assert by_key is not None
        assert by_key.job_id == job.job_id

    def test_list_jobs_filtering(self) -> None:
        repo = InMemoryJobRepository()
        j1 = JobRecord(
            job_type="ingest", state=JobState.SUCCEEDED, pipeline_run_id="run_1"
        )
        j2 = JobRecord(
            job_type="enrich", state=JobState.RUNNING, pipeline_run_id="run_1"
        )
        j3 = JobRecord(
            job_type="ingest", state=JobState.QUEUED, pipeline_run_id="run_2"
        )

        repo.save_job(j1)
        repo.save_job(j2)
        repo.save_job(j3)

        # Filter by pipeline_run_id
        run_1_jobs = repo.list_jobs(pipeline_run_id="run_1")
        assert len(run_1_jobs) == 2

        # Filter by state
        queued_jobs = repo.list_jobs(state=JobState.QUEUED)
        assert len(queued_jobs) == 1
        assert queued_jobs[0].job_id == j3.job_id

        # Filter by type
        ingest_jobs = repo.list_jobs(job_type="ingest")
        assert len(ingest_jobs) == 2


# ==============================================================================
# 4. Synchronous Job Runner
# ==============================================================================


class TestSyncJobRunner:
    """Test suite for SyncJobRunner execution engine."""

    def test_sync_runner_successful_execution(self) -> None:
        registry = JobRegistry()

        def custom_fn(ctx: JobContext, inp: Any) -> dict[str, Any]:
            ctx.report_progress(50.0, "Processing items")
            items = inp.get("items", [])
            return {"processed_count": len(items), "sum": sum(items)}

        registry.register(CallableJobHandler("calc", custom_fn))
        runner = SyncJobRunner(registry=registry)

        job = runner.create_job(
            job_type="calc",
            input_reference={"items": [10, 20, 30]},
            idempotency_key="calc_sum_001",
        )
        assert job.state == JobState.QUEUED

        # Run job synchronously
        result_job = runner.run_job(job.job_id)
        assert result_job.state == JobState.SUCCEEDED
        assert result_job.result_summary == {"processed_count": 3, "sum": 60}
        assert result_job.started_at is not None
        assert result_job.completed_at is not None

    def test_sync_runner_idempotent_deduplication(self) -> None:
        registry = JobRegistry()
        call_count = 0

        def sample_work(ctx: JobContext, inp: Any) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            return {"run": call_count}

        registry.register(CallableJobHandler("work", sample_work))
        runner = SyncJobRunner(registry=registry)

        # First submission
        job1 = runner.create_job("work", idempotency_key="idemp_key_unique")
        assert job1.state == JobState.QUEUED
        res1 = runner.run_job(job1.job_id)
        assert res1.state == JobState.SUCCEEDED
        assert call_count == 1

        # Duplicate submission with identical idempotency key
        job2 = runner.create_job("work", idempotency_key="idemp_key_unique")
        assert job2.job_id == job1.job_id
        assert job2.state == JobState.SUCCEEDED

        # Re-running already succeeded job returns existing record without re-executing
        res2 = runner.run_job(job2.job_id)
        assert res2.job_id == job1.job_id
        assert call_count == 1  # Handler not called again

    def test_sync_runner_failure_handling(self) -> None:
        registry = JobRegistry()

        def failing_fn(ctx: JobContext, inp: Any) -> Any:
            raise ValueError("Invalid mathematical operation in pipeline")

        registry.register(CallableJobHandler("fail_task", failing_fn))
        runner = SyncJobRunner(registry=registry)

        job = runner.create_job("fail_task")
        res = runner.run_job(job.job_id)

        assert res.state == JobState.FAILED
        assert res.error_code == ErrorCode.JOB_EXECUTION_ERROR.value
        assert "Invalid mathematical operation" in str(res.error_message_safe)

    def test_sync_runner_missing_config_blocked_state(self) -> None:
        registry = JobRegistry()

        def incomplete_config_fn(ctx: JobContext, inp: Any) -> Any:
            # Emulate missing scientific configuration per Section 21
            raise MissingConfigurationError(
                "Missing required parameters: ['spatial_cluster_radius_meters']"
            )

        registry.register(CallableJobHandler("scientific_stage", incomplete_config_fn))
        runner = SyncJobRunner(registry=registry)

        job = runner.create_job("scientific_stage")
        res = runner.run_job(job.job_id)

        # Canonical requirement: missing scientific configuration MUST trigger BLOCKED
        assert res.state == JobState.BLOCKED
        assert res.error_code == ErrorCode.MISSING_CONFIGURATION.value
        assert "spatial_cluster_radius_meters" in str(res.error_message_safe)

    def test_sync_runner_cancellation(self) -> None:
        registry = JobRegistry()

        def slow_cancel_fn(ctx: JobContext, inp: Any) -> Any:
            ctx.check_cancellation()
            return {"done": True}

        registry.register(CallableJobHandler("slow", slow_cancel_fn))
        runner = SyncJobRunner(registry=registry)

        # 1. Cancel while in queue
        job_queued = runner.create_job("slow")
        cancelled = runner.request_cancel(job_queued.job_id)
        assert cancelled.state == JobState.CANCELLED

        # Running a cancelled job returns immediately
        after_run = runner.run_job(cancelled.job_id)
        assert after_run.state == JobState.CANCELLED

    def test_pipeline_run_lifecycle_and_lineage(self) -> None:
        runner = SyncJobRunner()
        run = runner.create_pipeline_run(
            pipeline_name="real_flaring_pipeline",
            pipeline_version="v1.0.0",
            scientific_contract_id="contract_v1_jamnagar",
            input_snapshot_ids=["snap_firms_01", "snap_osm_01"],
        )
        assert run.status == PipelineRunStatus.RUNNING

        # Create child jobs linked to this pipeline run
        j1 = runner.create_job("ingest", pipeline_run_id=run.pipeline_run_id)
        assert j1.pipeline_run_id == run.pipeline_run_id

        # Finish pipeline run
        finished_run = runner.finish_pipeline_run(
            run.pipeline_run_id,
            status=PipelineRunStatus.SUCCEEDED,
            output_manifest_hash="sha256_output_manifest_12345",
        )
        assert finished_run.status == PipelineRunStatus.SUCCEEDED
        assert finished_run.completed_at is not None
        assert finished_run.output_manifest_hash == "sha256_output_manifest_12345"


# ==============================================================================
# 5. Canonical Domain Job Handlers
# ==============================================================================


class TestDomainJobHandlers:
    """Test suite for canonical domain job handlers."""

    def test_firms_ingest_job_handler(self) -> None:
        csv_content = (
            "latitude,longitude,brightness,scan,track,acq_date,acq_time,"
            "satellite,instrument,confidence,version,bright_t31,frp,daynight\n"
            "22.4707,70.0577,345.2,1.1,1.0,2026-08-20,0830,N,VIIRS,95,NRT,298.1,24.5,D\n"
            "22.4715,70.0585,350.1,1.1,1.0,2026-08-20,0830,N,VIIRS,98,NRT,300.2,30.0,D\n"
        )
        handler = FIRMSIngestJobHandler()
        ctx = JobContext(job_id="job_test_ingest", job_type=handler.job_type)

        res = handler.execute(
            ctx,
            {
                "csv_text": csv_content,
                "source_snapshot_id": "snap_test_001",
            },
        )
        assert res["detection_count"] == 2
        assert "firms" in res["source_ids"]

    def test_event_construct_job_handler(self) -> None:
        d1 = _create_sample_detection("d1", 22.4700, 70.0570)
        d2 = _create_sample_detection("d2", 22.4705, 70.0575)

        handler = EventConstructJobHandler()
        ctx = JobContext(job_id="job_test_construct", job_type=handler.job_type)

        res = handler.execute(ctx, {"detections": [d1, d2]})
        assert res["detection_count"] == 2
        assert res["event_count"] >= 1
        assert "dataset_id" in res

    def test_context_enrich_job_handler(self) -> None:
        events = [
            Event(
                event_id="ev_test_01",
                detection_ids=["d1"],
                detection_count=1,
                centroid_geometry=Coordinate(latitude=22.4700, longitude=70.0570),
                started_at=datetime(2026, 8, 20, 10, 0, 0, tzinfo=UTC),
                ended_at=datetime(2026, 8, 20, 10, 0, 0, tzinfo=UTC),
                formation_configuration_id="contract_test",
                formation_configuration_version="v1.0.0",
            )
        ]
        context_feat = ContextFeature(
            feature_id="cf_refinery_01",
            provider="osm",
            dataset_name="planet_osm_polygon",
            dataset_version="v1.0",
            context_type=ContextType.OIL_GAS,
            geometry=Coordinate(latitude=22.4702, longitude=70.0572),
            facility_name="Reliance Refinery Complex",
        )

        handler = ContextEnrichJobHandler()
        ctx = JobContext(job_id="job_test_enrich", job_type=handler.job_type)

        res = handler.execute(
            ctx,
            {
                "events": events,
                "context_features": [context_feat],
            },
        )
        assert res["enriched_event_count"] == 1
        assert res["evidence_item_count"] >= 1

    def test_intelligence_classify_job_handler(self) -> None:
        events = [
            Event(
                event_id="ev_test_01",
                detection_ids=["d1"],
                detection_count=1,
                centroid_geometry=Coordinate(latitude=22.4700, longitude=70.0570),
                started_at=datetime(2026, 8, 20, 10, 0, 0, tzinfo=UTC),
                ended_at=datetime(2026, 8, 20, 10, 0, 0, tzinfo=UTC),
                formation_configuration_id="contract_test",
                formation_configuration_version="v1.0.0",
            )
        ]

        handler = IntelligenceClassifyJobHandler()
        ctx = JobContext(job_id="job_test_classify", job_type=handler.job_type)

        res = handler.execute(ctx, {"events": events, "sources": []})
        assert res["intelligence_results_count"] == 1
        assert "phenomenon_distribution" in res

    def test_end_to_end_pipeline_job_handler(self) -> None:
        d1 = _create_sample_detection("d1", 22.4700, 70.0570)
        d2 = _create_sample_detection("d2", 22.4705, 70.0575)

        handler = EndToEndPipelineJobHandler()
        ctx = JobContext(
            job_id="job_test_e2e",
            job_type=handler.job_type,
            pipeline_run_id="run_e2e_001",
        )

        res = handler.execute(ctx, {"detections": [d1, d2]})
        assert res["status"] == "success"
        assert res["detection_count"] == 2
        assert res["event_count"] >= 1
        assert res["intelligence_results_count"] >= 1


# ==============================================================================
# 6. Security and Secret Sanitization
# ==============================================================================


class TestJobSecurityAndSanitization:
    """Validate that credentials are never stored in metadata or errors."""

    def test_sensitive_tokens_scrubbed_from_job_input_and_metadata(self) -> None:
        runner = SyncJobRunner()
        job = runner.create_job(
            job_type="custom",
            input_reference={
                "map_key": "SECRET_FIRMS_MAP_KEY_12345",
                "normal_param": "jamnagar_bbox",
            },
            metadata={
                "password": "SUPER_SECRET_DB_PASSWORD",
                "api_key": "API_SECRET_TOKEN_9999",
                "author": "analyst_1",
            },
        )

        assert job.input_reference is not None
        assert "SECRET_FIRMS_MAP_KEY_12345" not in str(job.input_reference)
        assert job.input_reference["map_key"] == "[REDACTED]"
        assert job.input_reference["normal_param"] == "jamnagar_bbox"

        assert "SUPER_SECRET_DB_PASSWORD" not in str(job.metadata)
        assert "API_SECRET_TOKEN_9999" not in str(job.metadata)
        assert job.metadata["password"] == "[REDACTED]"
        assert job.metadata["author"] == "analyst_1"

    def test_secrets_scrubbed_from_error_messages(self) -> None:
        registry = JobRegistry()

        def failing_with_secret_fn(ctx: JobContext, inp: Any) -> Any:
            raise ValueError(
                "Failed api_key=SECRET_XYZ_98765 for map_key=FIRMS_KEY_999"
            )

        registry.register(
            CallableJobHandler("secret_leak_task", failing_with_secret_fn)
        )
        runner = SyncJobRunner(registry=registry)

        job = runner.create_job("secret_leak_task")
        res = runner.run_job(job.job_id)

        assert res.state == JobState.FAILED
        assert res.error_message_safe is not None
        assert "SECRET_XYZ_98765" not in res.error_message_safe
        assert "FIRMS_KEY_999" not in res.error_message_safe
