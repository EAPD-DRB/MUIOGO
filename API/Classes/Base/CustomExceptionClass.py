"""Custom exception class for API error responses."""

from typing import Any, Dict, Optional, Tuple, Union


class CustomException(Exception):
    """Application-specific exception that carries an HTTP status code.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code to return (default ``400``).
        payload: Optional extra data included in the JSON response.
    """

    status_code: int = 400

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        payload: Optional[Union[Dict[str, Any], Tuple[Any, ...]]] = None,
    ) -> None:
        """Initialise a ``CustomException``.

        Args:
            message: Human-readable error description.
            status_code: HTTP status code override. Uses class default
                (``400``) when *None*.
            payload: Additional key/value data to include in the
                serialised error response.
        """
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the exception to a dictionary.

        Returns:
            Dictionary containing the payload (if any) plus the
            ``message`` key.
        """
        rv: Dict[str, Any] = dict(self.payload or ())
        rv['message'] = self.message
        return rv