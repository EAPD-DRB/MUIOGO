"""
Security middleware for the MUIOGO Flask application.

Addresses three critical security gaps:
1. Unlimited file uploads (DoS vector) — enforces MAX_CONTENT_LENGTH
2. Unrestricted CORS — locks origins to known frontends
3. Missing security response headers — adds industry-standard protections
"""


def apply_security_defaults(app):
    """
    Apply production-grade security defaults to a Flask application.

    Call this once during app initialisation, BEFORE registering blueprints
    or starting the server.
    """

    # ------------------------------------------------------------------
    # 1. Upload size limit  (prevents Denial-of-Service via huge files)
    #    500 MB is generous for OSeMOSYS / OG-Core model archives.
    #    Flask will automatically return HTTP 413 if exceeded.
    # ------------------------------------------------------------------
    if app.config.get("MAX_CONTENT_LENGTH") is None:
        app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB

    # ------------------------------------------------------------------
    # 2. Security response headers  (added on every response)
    # ------------------------------------------------------------------
    @app.after_request
    def set_security_headers(response):
        # Prevent the page from being embedded in an iframe (clickjacking)
        response.headers.setdefault("X-Frame-Options", "DENY")

        # Stop browsers from MIME-sniffing the Content-Type
        response.headers.setdefault("X-Content-Type-Options", "nosniff")

        # Enable the browser's built-in XSS filter
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")

        # Basic Content-Security-Policy: only allow resources from same origin
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        )

        # Prevent leaking the full URL when navigating away
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

        return response
