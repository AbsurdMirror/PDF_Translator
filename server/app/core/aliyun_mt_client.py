# -*- coding: utf-8 -*-
import logging

from alibabacloud_alimt20181012.client import Client as alimt20181012Client
from alibabacloud_alimt20181012 import models as alimt_20181012_models
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

logger = logging.getLogger(__name__)

default_endpoint = "mt.aliyuncs.com"

class AliyunMTClient:
    def __init__(self, access_key_id: str, access_key_secret: str, region_id: str = "cn-hangzhou", endpoint: str = default_endpoint):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.region_id = region_id
        self.endpoint = endpoint.replace("https://", "").replace("http://", "").strip()
        if not self.endpoint:
            self.endpoint = default_endpoint
        if "/" in self.endpoint:
            self.endpoint = self.endpoint.split("/")[0]
        self.client = self._init_client()

    def _init_client(self) -> alimt20181012Client:
        config = open_api_models.Config(endpoint=self.endpoint)
        if self.access_key_id and self.access_key_secret:
            config.access_key_id = self.access_key_id
            config.access_key_secret = self.access_key_secret
            config.type = "access_key"
        else:
            credential = CredentialClient()
            config.credential = credential
        return alimt20181012Client(config)

    def translate_general(self, source_text: str, source_lang: str, target_lang: str) -> str:
        """
        Call Aliyun Machine Translation TranslateGeneral API
        """
        request = alimt_20181012_models.TranslateGeneralRequest(
            format_type="text",
            scene="general",
            source_language=source_lang,
            target_language=target_lang,
            source_text=source_text,
        )
        runtime = util_models.RuntimeOptions()
        try:
            resp = self.client.translate_general_with_options(request, runtime)
            translated = self._extract_translated(resp)
            return translated
        except Exception as e:
            logger.error(f"Aliyun MT request failed: {e}")
            raise

    def _extract_translated(self, resp) -> str:
        body = getattr(resp, "body", None)
        if body is not None:
            code = getattr(body, "code", None) or getattr(body, "Code", None)
            if code is not None and str(code) != "200":
                message = getattr(body, "message", None) or getattr(body, "Message", None)
                raise Exception(f"Aliyun API Error: {message} (Code: {code})")
            data = getattr(body, "data", None) or getattr(body, "Data", None)
            translated = None
            if data is not None:
                translated = getattr(data, "translated", None) or getattr(data, "Translated", None)
            if translated is not None:
                return translated

        result = None
        try:
            result = resp.to_map()
        except Exception:
            result = None
        if isinstance(result, dict):
            body = result.get("body") or result.get("Body") or result
            if isinstance(body, dict):
                code = body.get("Code") or body.get("code")
                if code is not None and str(code) != "200":
                    message = body.get("Message") or body.get("message")
                    raise Exception(f"Aliyun API Error: {message} (Code: {code})")
                data = body.get("Data") or body.get("data")
                if isinstance(data, dict):
                    translated = data.get("Translated") or data.get("translated")
                    if translated is not None:
                        return translated

        raise Exception("Unexpected response format")
