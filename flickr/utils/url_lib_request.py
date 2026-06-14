import base64
import json
import logging
import os
import ssl
import time
from datetime import datetime, timezone
from typing import Dict, Tuple

import urllib3
from urllib3.util.retry import Retry

from flickr.utils.url_lib_response import URLLibResponse


logger = logging.getLogger(__name__)


class URLLibRequest:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    retries = None
    if os.environ.get("RETRY_ENABLED", False):
        retries = Retry(
            total=2,
            backoff_factor=0,
            status_forcelist=[503, 504],
            allowed_methods=["GET", "POST"],
        )

    http = urllib3.PoolManager(cert_reqs="CERT_NONE", ssl_context=context, maxsize=100, retries=retries)

    def __init__(self, method, url, headers, body):
        self.method = method
        self.url = url
        self.headers = headers
        self.body = body

    @classmethod
    def validate_headers(cls, headers: Dict):
        if not headers:
            return
        headers_to_delete = [key for key in headers.keys() if key.lower() == "content-length"]
        for header in headers_to_delete:
            del headers[header]

    @classmethod
    def send(
        cls,
        url: str,
        data: str = None,
        headers: Dict = None,
        method: str = None,
        timeout: int = int(os.getenv("HTTP_READ_TIMEOUT", 45)),
        auth: Tuple = (),
        params: Dict = {},
        *args,
        **kwargs,
    ) -> URLLibResponse:
        headers = headers or {}

        timeout = int(os.getenv("HTTP_READ_TIMEOUT", kwargs.get("timeout", timeout)))

        timestamp = datetime.now(timezone.utc).isoformat()
        if auth:
            headers.update({"Authorization": f"Basic {cls._makeBasicAuthString(auth)}"})
        method = method or "GET"
        json_data = kwargs.get("json")
        if json_data:
            data = json.dumps(json_data)

        cls.validate_headers(headers)

        start_time = time.time()
        response = None

        try:
            response = cls.http.request(
                method=method,
                url=url,
                headers=headers,
                body=data if data else None,
                timeout=urllib3.Timeout(connect=timeout, read=timeout),
                preload_content=False,
                fields=params,
            )
            elapsed = time.time() - start_time
            logger.debug(f"elapsed time for {method} {url}: {elapsed:.2f} seconds")
            return URLLibResponse(response=response, elapsed=elapsed, request=cls(method, url, headers, data), timestamp=timestamp)
        finally:
            if response is not None:
                response.release_conn()

    @classmethod
    def _makeBasicAuthString(cls, auth: Tuple = ()):
        if len(auth) != 2:
            raise ValueError("Auth tuple must contain exactly two elements (username, password)")
        aut_string = f"{auth[0]}:{auth[1]}".encode("utf-8")
        return base64.b64encode(aut_string).decode("utf-8")

    @classmethod
    def post(cls, url: str, data: str = None, headers: Dict = None, auth: Tuple = (), *args, **kwargs) -> URLLibResponse:
        return cls.send(url=url, data=data, headers=headers, method="POST", auth=auth, *args, **kwargs)

    @classmethod
    def get(cls, url: str, data: str = None, headers: Dict = None, auth: Tuple = (), *args, **kwargs) -> URLLibResponse:
        return cls.send(url=url, data=data, headers=headers, method="GET", auth=auth, *args, **kwargs)

    @classmethod
    def put(cls, url: str, data: str = None, headers: Dict = None, auth: Tuple = (), *args, **kwargs) -> URLLibResponse:
        return cls.send(url=url, data=data, headers=headers, method="PUT", auth=auth, *args, **kwargs)

    @classmethod
    def head(cls, url: str, data: str = None, headers: Dict = None, auth: Tuple = (), *args, **kwargs) -> URLLibResponse:
        return cls.send(url=url, data=data, headers=headers, method="HEAD", auth=auth, *args, **kwargs)

    @classmethod
    def delete(cls, url: str, data: str = None, headers: Dict = None, auth: Tuple = (), *args, **kwargs) -> URLLibResponse:
        return cls.send(url=url, data=data, headers=headers, method="DELETE", auth=auth, *args, **kwargs)

    @classmethod
    def patch(cls, url: str, data: str = None, headers: Dict = None, auth: Tuple = (), *args, **kwargs) -> URLLibResponse:
        return cls.send(url=url, data=data, headers=headers, method="PATCH", auth=auth, *args, **kwargs)

    @classmethod
    def options(cls, url: str, data: str = None, headers: Dict = None, auth: Tuple = (), *args, **kwargs) -> URLLibResponse:
        return cls.send(url=url, data=data, headers=headers, method="OPTIONS", auth=auth, *args, **kwargs)
