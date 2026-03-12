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
    assert 'href="/linkedin-login/"' in html


@pytest.mark.django_db
def test_linkedin_login_requires_staff():
    """LinkedIn Login page redirects to admin login when not staff."""
    client = Client()
    response = client.get("/linkedin-login/")
    assert response.status_code == 302
    assert "/admin/login/" in response["Location"]


@pytest.mark.django_db
def test_linkedin_login_staff_can_access(fake_session):
    """Staff user can access LinkedIn Login page."""
    client = Client()
    client.force_login(fake_session.django_user)
    response = client.get("/linkedin-login/")
    assert response.status_code == 200
    assert b"LinkedIn Login" in response.content
    assert b"Paste cookies" in response.content
