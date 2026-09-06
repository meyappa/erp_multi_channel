from app.services.inventory import resolve_conflict


def test_erp_wins():
    winner, rule = resolve_conflict(40, 18, "erp_wins", True)
    assert winner == 40
    assert rule == "erp_wins"


def test_marketplace_wins():
    winner, rule = resolve_conflict(40, 18, "marketplace_wins", True)
    assert winner == 18


def test_newest_wins():
    winner, rule = resolve_conflict(40, 18, "newest_wins", False)
    assert winner == 18
    winner, rule = resolve_conflict(40, 18, "newest_wins", True)
    assert winner == 40


def test_no_conflict():
    winner, rule = resolve_conflict(10, 10, "erp_wins", True)
    assert rule == "no_conflict"
