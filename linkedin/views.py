"""
Web views for the linkedin app.
"""

from django.shortcuts import render


def landing_page(request):
    """
    Root URL landing page. Lets users choose between CRM and Django Admin.
    """
    return render(request, "linkedin/landing.html")
