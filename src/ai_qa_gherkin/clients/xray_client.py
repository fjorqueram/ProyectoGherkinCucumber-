from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from ai_qa_gherkin.config import settings
from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models.domain import XrayImportResponse
from ai_qa_gherkin.retry import PermanentError, TransientError, retry_policy

log = get_logger("xray_client")


class XrayClient:
    def __init__(self) -> None:
        self.base_url = settings.xray_base_url.rstrip("/")
        self.client_id = settings.xray_client_id
        self.client_secret = settings.xray_client_secret
        self.timeout = settings.xray_timeout_seconds
        self.xray_token: str | None = None

    def _handle_error(self, response: httpx.Response) -> None:
        if response.status_code in (429, 500, 502, 503, 504):
            raise TransientError(f"Xray transient: {response.status_code}: {response.text[:300]}")
        raise PermanentError(f"Xray permanent: {response.status_code}: {response.text[:300]}")

    @retry_policy()
    def authenticate(self) -> str:
        url = f"{self.base_url}/api/v2/authenticate"
        payload = {"client_id": self.client_id, "client_secret": self.client_secret}
        log.info("Authenticating with Xray...")

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload)
                if response.status_code >= 400:
                    self._handle_error(response)

                token = response.text.strip().replace('"', "")
                if not token:
                    raise PermanentError("Empty Xray token")

                self.xray_token = token
                return token
        except httpx.TimeoutException as e:
            raise TransientError(f"Xray timeout: {e}") from e
        except httpx.NetworkError as e:
            raise TransientError(f"Xray network error: {e}") from e

    def _auth_headers(self) -> dict[str, str]:
        if not self.xray_token:
            self.authenticate()
        return {"Authorization": f"Bearer {self.xray_token}"}

    @retry_policy()
    def import_feature_cucumber(
        self,
        project_key: str,
        feature_text: str,
        test_type_name: str,
        file_name: str = "smoke.feature",
    ) -> dict[str, Any]:
        token = self.authenticate()

        url = (
            f"{self.base_url}/api/v2/import/feature"
            f"?projectKey={project_key}"
            f"&testType={quote(test_type_name)}"
        )

        headers = {"Authorization": f"Bearer {token}"}
        files = {"file": (file_name, feature_text.encode("utf-8"), "text/plain")}

        log.info(
            f"Importing Cucumber feature to Xray project={project_key} testType={test_type_name}"
        )

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, headers=headers, files=files)
                if response.status_code >= 400:
                    self._handle_error(response)

                try:
                    data = response.json()
                    return data if isinstance(data, dict) else {"raw": data}
                except ValueError:
                    txt = response.text.strip()
                    if txt:
                        return {"raw": txt}
                    raise PermanentError("Invalid Xray import response")
        except httpx.TimeoutException as e:
            raise TransientError(f"Xray timeout: {e}") from e
        except httpx.NetworkError as e:
            raise TransientError(f"Xray network error: {e}") from e

    @retry_policy()
    def import_execution_results(
        self, cucumber_json: dict[str, Any], project_key: str
    ) -> XrayImportResponse:
        url = f"{self.base_url}/api/v2/import/execution/cucumber"
        params = {"projectKey": project_key}
        headers = {**self._auth_headers(), "Content-Type": "application/json"}

        log.info(f"Importing execution results to Xray project={project_key}")

        try:
            with httpx.Client(timeout=self.timeout, headers=headers) as client:
                response = client.post(url, params=params, json=cucumber_json)
                if response.status_code >= 400:
                    self._handle_error(response)

                return XrayImportResponse(
                    success=True,
                    payload=response.json() if response.text else {},
                )
        except httpx.TimeoutException as e:
            raise TransientError(f"Xray timeout: {e}") from e
        except httpx.NetworkError as e:
            raise TransientError(f"Xray network error: {e}") from e