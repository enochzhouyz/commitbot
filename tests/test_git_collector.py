from packages.components.collectors.git import GitCollector


def test_git_collector_returns_events_for_repo() -> None:
    events = GitCollector(".").collect()

    assert any(event.type == "git.diff_snapshot" for event in events)
    assert any(event.type == "git.commit" for event in events)

