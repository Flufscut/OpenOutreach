"""
Tests for the root URL landing page.
"""

import pytest
from django.test import Client


@pytest.mark.django_db
def test_landing_page_returns_200():
    """Root URL returns 200 and renders the landing page."""
    client = Client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"OpenOutreach" in response.content
    assert b"/crm/" in response.content
    assert b"/admin/" in response.content


@pytest.mark.django_db
def test_landing_page_has_crm_and_admin_links():
    """Landing page contains links to CRM and Django Admin."""
    client = Client()
    response = client.get("/")
    assert response.status_code == 200
    html = response.content.decode()
    assert 'href="/crm/"' in html
    assert 'href="/admin/"' in html
