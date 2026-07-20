from readmatch_ai.domain.user import UserId


def test_user_id_generate_is_unique() -> None:
    assert UserId.generate() != UserId.generate()
