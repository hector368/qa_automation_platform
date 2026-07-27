from django.http import HttpRequest, HttpResponse


def home(request: HttpRequest) -> HttpResponse:
    """Comprueba que la aplicación esté correctamente registrada."""

    return HttpResponse("Test Case Generator ready")