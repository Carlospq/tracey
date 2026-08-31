"""Smoke tests — the app boots and serves its public pages against a real
(empty) copy of the production schema. This is the safety net for dependency
and Django-version upgrades: it catches breakage that a bare `import` misses
(URLconf resolution, middleware, template rendering, ORM queries at import).
"""
import pytest

pytestmark = pytest.mark.django_db


def test_robots_txt(client):
    resp = client.get("/robots.txt")
    assert resp.status_code == 200


def test_admin_login_renders(client):
    resp = client.get("/admin/login/")
    assert resp.status_code == 200


def test_home(client):
    # home redirects anonymous users; either is fine, a 500 is not.
    resp = client.get("/")
    assert resp.status_code in (200, 302)


def test_query_page(client):
    from django.urls import reverse

    resp = client.get(reverse("query"))
    assert resp.status_code == 200


def test_security_headers_present(client):
    resp = client.get("/robots.txt")
    assert "Content-Security-Policy" in resp.headers
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_schema_tables_exist():
    """The managed=False models resolve against the loaded test schema."""
    from apps.home.models import Domains, Sequences

    assert Domains.objects.count() == 0
    assert Sequences.objects.count() == 0
