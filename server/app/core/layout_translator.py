import json
import logging
import time
from typing import Callable, Dict, List, Optional, Tuple, Union
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

logger = logging.getLogger(__name__)


class LayoutTranslator:
    def __init__(
        self,
        api_key: str = "",
        source_lang: str = "auto",
        target_lang: str = "Chinese",
        model: str = "qwen-mt-flash",
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        request_timeout_seconds: int = 60,
        max_retries: int = 3,
        retry_backoff_seconds: float = 1.0,
    ):
        self.api_key = api_key or ""
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.model = model
        self.base_url = (base_url or "").rstrip("/")
        self.request_timeout_seconds = int(request_timeout_seconds)
        self.max_retries = int(max_retries)
        self.retry_backoff_seconds = float(retry_backoff_seconds)

    def translate_yaml_file(
        self,
        input_yaml_path: str,
        output_yaml_path: Optional[str] = None,
        on_item: Optional[Callable[[int, str, bool], None]] = None,
    ) -> List[Dict]:
        output_yaml_path = output_yaml_path or input_yaml_path
        data, layouts = self._load_yaml_layouts(input_yaml_path)
        self.translate_layouts(layouts, on_item=on_item)
        self._save_yaml_layouts(output_yaml_path, data, layouts)
        return layouts

    def translate_layouts(
        self,
        layouts: List[Dict],
        on_item: Optional[Callable[[int, str, bool], None]] = None,
    ) -> List[Dict]:
        for idx, item in enumerate(layouts):
            layout_type = item.get("type")
            if layout_type == "figure":
                result = item.get("markdownContent") or ""
                if on_item:
                    on_item(idx, result, True)
                continue

            content = item.get("markdownContent") or ""
            if content == "":
                if on_item:
                    on_item(idx, "", True)
                continue

            translated = self._translate_text(content)
            item["translatedMarkdownContent"] = translated

            if on_item:
                on_item(idx, translated, False)

        return layouts

    def _translate_text(self, text: str) -> str:
        if self.api_key == "":
            raise ValueError("api_key 不能为空")

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": text}],
            "extra_body": {
                "translation_options": {
                    "source_lang": self.source_lang,
                    "target_lang": self.target_lang,
                }
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._post_json(url, payload, headers=headers)
                content = (
                    response.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                if not isinstance(content, str) or content == "":
                    raise ValueError("模型返回为空")
                return content
            except Exception as e:
                last_error = e
                if attempt >= self.max_retries:
                    break
                sleep_seconds = self.retry_backoff_seconds * attempt
                time.sleep(sleep_seconds)

        raise RuntimeError(f"翻译失败: {last_error}") from last_error

    def _post_json(self, url: str, payload: Dict, headers: Dict) -> Dict:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = Request(url=url, data=data, headers=headers, method="POST")
        try:
            with urlopen(req, timeout=self.request_timeout_seconds) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except HTTPError as e:
            try:
                raw = e.read().decode("utf-8")
            except Exception:
                raw = ""
            raise RuntimeError(f"HTTP {e.code}: {raw}") from e
        except URLError as e:
            raise RuntimeError(f"网络错误: {e}") from e

    def _load_yaml_layouts(self, yaml_path: str) -> Tuple[Union[Dict, List], List[Dict]]:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if isinstance(data, dict):
            layouts = data.get("layouts", [])
            if layouts is None:
                layouts = []
            if not isinstance(layouts, list):
                raise ValueError("YAML 的 layouts 字段不是数组")
            return data, layouts

        if isinstance(data, list):
            return data, data

        raise ValueError("YAML 根节点必须是 dict 或 list")

    def _save_yaml_layouts(self, yaml_path: str, data: Union[Dict, List], layouts: List[Dict]) -> None:
        if isinstance(data, dict):
            data["layouts"] = layouts
            to_write: Union[Dict, List] = data
        else:
            to_write = layouts

        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(to_write, f, allow_unicode=True, sort_keys=False)

