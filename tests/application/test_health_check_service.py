from readmatch_ai.application.health_check_service import HealthCheckService


def test_check_reports_a_healthy_application() -> None:
    service = HealthCheckService()

    status = service.check()

    assert status.healthy is True
    assert any(check.name == "process" and check.available for check in status.checks)


def test_check_is_deterministic_across_repeated_calls() -> None:
    service = HealthCheckService()

    first = service.check()
    second = service.check()

    assert first == second
