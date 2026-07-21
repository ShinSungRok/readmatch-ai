from readmatch_ai.domain.health import ComponentCheck, HealthStatus, ReadinessStatus


def test_health_status_is_healthy_when_all_checks_are_available() -> None:
    status = HealthStatus(
        healthy=True, checks=(ComponentCheck(name="process", available=True),)
    )

    assert status.healthy is True
    assert status.checks[0].name == "process"


def test_component_check_detail_defaults_to_none() -> None:
    check = ComponentCheck(name="process", available=True)

    assert check.detail is None


def test_readiness_status_reports_an_unavailable_check_with_detail() -> None:
    status = ReadinessStatus(
        ready=False,
        checks=(
            ComponentCheck(name="book_repository", available=False, detail="RuntimeError"),
        ),
    )

    assert status.ready is False
    assert status.checks[0].detail == "RuntimeError"
