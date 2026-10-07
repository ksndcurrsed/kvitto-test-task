from app.main import create_app


def test_app_exposes_required_routes() -> None:
    paths = set(create_app().openapi()["paths"])
    assert {"/tariffs", "/payments", "/payments/{payment_id}", "/webhooks/bank"} <= paths
