import urllib3


class Elapsed:
    def __init__(self, elapsed: float | None = None) -> None:
        self.elapsed = elapsed

    def total_seconds(self) -> float:
        if self.elapsed:
            return abs(self.elapsed)
        return 0


class URLLibResponse:
    def __init__(
        self,
        response: urllib3.response.HTTPResponse | None = None,
        elapsed: float | None = None,
        request: object | None = None,
        timestamp: str | None = None,
    ) -> None:
        self.request = request
        self.response = response
        self.headers = response and dict(response.headers)
        self.timestamp = timestamp
        self.parsed_json: dict | list | None = None
        self.status_code: int = 408

        content = getattr(response, "content", None)
        self._data = response and getattr(response, "data", content)

        text = getattr(response, "data", b"").decode("UTF-8")
        self.reason = response and getattr(response, "reason", text)

        if response and getattr(response, "status_code", None):
            self.status_code = response.status_code
        elif response and getattr(response, "status", None):
            self.status_code = response.status

        self.elapsed = Elapsed(elapsed=elapsed)
        self.url = self.request.url if self.request else None

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def data(self) -> bytes | None:
        return self._data

    @data.setter
    def data(self, value: bytes | None) -> None:
        self._data = value

    @property
    def text(self) -> str:
        return self._data.decode("utf-8", errors="replace") if self._data else ""

    @property
    def _content(self) -> bytes | None:
        return self._data

    @property
    def content(self) -> bytes | None:
        return self._data

    @_content.setter
    def _content(self, value: bytes | None) -> None:
        self._data = value

    def json(self) -> dict:
        import json

        if not self.parsed_json:
            self.parsed_json = json.loads(self.text) if self.text else None
        return self.parsed_json
