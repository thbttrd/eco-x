"""FastAPI middleware for i18n language detection and persistence."""

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ecox_client.i18n.loader import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES

# Type alias for the call_next function
RequestResponseEndpoint = Callable[[Request], Awaitable[Response]]

# Cookie settings for language preference
LANG_COOKIE_NAME = "lang"
LANG_COOKIE_MAX_AGE = 365 * 24 * 60 * 60  # 1 year in seconds


class I18nMiddleware(BaseHTTPMiddleware):
    """Middleware to detect and persist user language preference.

    Language detection priority:
    1. URL query parameter (?lang=fr) - for shareable links
    2. Cookie - for persistent preference
    3. Default language (en)

    When language is set via URL param, a cookie is set for persistence.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request and set language in request.state."""
        lang = self._detect_language(request)
        request.state.lang = lang

        # Check if language was explicitly set via URL param
        url_lang = request.query_params.get("lang")

        response: Response = await call_next(request)

        # Set cookie if language was changed via URL param
        if url_lang and url_lang in SUPPORTED_LANGUAGES:
            response.set_cookie(
                key=LANG_COOKIE_NAME,
                value=url_lang,
                max_age=LANG_COOKIE_MAX_AGE,
                httponly=True,
                samesite="lax",
            )

        return response

    def _detect_language(self, request: Request) -> str:
        """Detect language from request.

        Priority: URL param > Cookie > Default
        """
        # 1. Check URL query parameter
        url_lang = request.query_params.get("lang")
        if url_lang and url_lang in SUPPORTED_LANGUAGES:
            return url_lang

        # 2. Check cookie
        cookie_lang = request.cookies.get(LANG_COOKIE_NAME)
        if cookie_lang and cookie_lang in SUPPORTED_LANGUAGES:
            return cookie_lang

        # 3. Fall back to default
        return DEFAULT_LANGUAGE
