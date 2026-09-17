import sys

sys.path.insert(0, "services/strategy-engine")

from app.seed import seed_strategies, SEED_STRATEGIES


def test_seed_inserts_strategies(db_session):
    inserted = seed_strategies(db_session)
    assert inserted == len(SEED_STRATEGIES)

    from common.models.strategy import Strategy
    rows = db_session.query(Strategy).all()
    codes = {r.code for r in rows}
    assert len(codes) >= len(SEED_STRATEGIES)


def test_seed_is_idempotent(db_session):
    seed_strategies(db_session)
    seed_strategies(db_session)
    from common.models.strategy import Strategy
    rows = db_session.query(Strategy).all()
    assert len(rows) == len(SEED_STRATEGIES)