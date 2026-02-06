# -*- coding: utf-8 -*-
import hashlib
import hmac
import base64
import uuid
import urllib.parse
import datetime
import requests
import logging
import json

logger = logging.getLogger(__name__)

class AliyunMTClient:
    def __init__(self, access_key_id: str, access_key_secret: str, region_id: str = "cn-hangzhou", endpoint: str = "mt.cn-hangzhou.aliyuncs.com"):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.region_id = region_id
        # Ensure endpoint doesn't have protocol
        self.endpoint = endpoint.replace("https://", "").replace("http://", "").strip()
        if not self.endpoint:
            self.endpoint = "mt.cn-hangzhou.aliyuncs.com"

    def translate_general(self, source_text: str, source_lang: str, target_lang: str) -> str:
        """
        Call Aliyun Machine Translation TranslateGeneral API
        """
        # API Parameters
        params = {
            "Action": "TranslateGeneral",
            "FormatType": "text",
            "Scene": "general",
            "SourceLanguage": source_lang,
            "TargetLanguage": target_lang,
            "SourceText": source_text,
            "AccessKeyId": self.access_key_id,
            "SignatureMethod": "HMAC-SHA1",
            "Timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "SignatureVersion": "1.0",
            "SignatureNonce": str(uuid.uuid4()),
            "Version": "2018-10-12",
            "RegionId": self.region_id
        }

        # Calculate Signature
        params["Signature"] = self._calculate_signature(params, "POST")

        # Make Request
        url = f"https://{self.endpoint}/"
        try:
            # Using POST with data form-urlencoded as typical for RPC
            response = requests.post(url, data=params, timeout=10)
            response.raise_for_status()

            result = response.json()

            if "Code" in result and str(result["Code"]) != "200":
                raise Exception(f"Aliyun API Error: {result.get('Message')} (Code: {result.get('Code')})")

            if "Data" in result and "Translated" in result["Data"]:
                return result["Data"]["Translated"]

            # XML response fallback? The doc says JSON format if not specified or FormatType?
            # Actually the doc says "FormatType" is for text format (html/text), not response format.
            # But normally Aliyun APIs return JSON by default or based on Accept header.
            # We'll assume JSON.

            raise Exception(f"Unexpected response format: {result}")

        except Exception as e:
            logger.error(f"Aliyun MT request failed: {e}")
            raise

    def _calculate_signature(self, params: dict, method: str) -> str:
        # 1. Sort parameters
        sorted_keys = sorted(params.keys())

        # 2. Canonicalized Query String
        canonicalized_query_string = ""
        for key in sorted_keys:
            value = str(params[key])
            encoded_key = self._percent_encode(key)
            encoded_value = self._percent_encode(value)
            canonicalized_query_string += f"&{encoded_key}={encoded_value}"

        # Remove leading &
        canonicalized_query_string = canonicalized_query_string[1:]

        # 3. StringToSign
        string_to_sign = method + "&" + self._percent_encode("/") + "&" + self._percent_encode(canonicalized_query_string)

        # 4. Signature
        key = self.access_key_secret + "&"
        signature = hmac.new(key.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha1).digest()
        signature_base64 = base64.b64encode(signature).decode("utf-8")

        return signature_base64

    def _percent_encode(self, s: str) -> str:
        # Aliyun specific encoding rules
        res = urllib.parse.quote(s.encode("utf-8"), safe="")
        res = res.replace("+", "%20")
        res = res.replace("*", "%2A")
        res = res.replace("%7E", "~")
        return res
