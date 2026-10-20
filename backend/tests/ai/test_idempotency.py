from backend.app.ai.idempotency import IdempotencyStore


def test_job_is_not_completed_initially():
    store = IdempotencyStore()

    assert store.has_completed("job-001") is False


def test_completed_job_is_detected():
    store = IdempotencyStore()

    store.save(
        "job-001",
        {"status": "done"},
    )

    assert store.has_completed("job-001") is True


def test_completed_result_can_be_reused():
    store = IdempotencyStore()

    result = {
        "status": "done",
        "entities": [],
    }

    store.save(
        "job-001",
        result,
    )

    assert store.get("job-001") == result


def test_clear_removes_completed_job():
    store = IdempotencyStore()

    store.save(
        "job-001",
        {"status": "done"},
    )

    store.clear("job-001")

    assert store.has_completed("job-001") is False