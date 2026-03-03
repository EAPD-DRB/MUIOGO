class VersionMismatchException(Exception):
    def __init__(self, expected, detected):
        self.expected = expected
        self.detected = detected
        super().__init__(
            f"Model version mismatch: expected {expected}, detected {detected}"
        )