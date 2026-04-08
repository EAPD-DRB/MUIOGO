"""Shared utility helpers for Flask API routes."""
from flask import jsonify, request


def validate_json_fields(*fields):
    """Validate that the request body is JSON and contains all required fields.

    Returns (None, None) when valid.
    Returns (response, 400) when invalid.
    """
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Request body must be valid JSON"}), 400
    for field in fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    return None, None
