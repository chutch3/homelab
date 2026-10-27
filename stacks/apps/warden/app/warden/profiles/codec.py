from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from yaml.nodes import MappingNode

from warden.profiles.models import ProfileDocument
from warden.profiles.reading import ProfileFile


class _UniqueSafeLoader(yaml.SafeLoader):
    def construct_mapping(self, node: MappingNode, deep: bool = False) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ValueError("mapping keys must be strings")
            if key in result:
                raise ValueError(f"duplicate key {key!r}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


class YamlJsonCodec:
    def __init__(self, schemas: Mapping[str, dict[str, Any]]) -> None:
        self.validators = {kind: Draft202012Validator(schema) for kind, schema in schemas.items()}

    def decode(self, entry: ProfileFile, content: bytes) -> ProfileDocument:
        try:
            data = yaml.load(content.decode("utf-8"), Loader=_UniqueSafeLoader)
        except yaml.YAMLError as exc:
            raise ValueError(str(exc)) from exc
        errors = list(self.validators[entry.kind].iter_errors(data))
        if errors:
            details = []
            for error in errors:
                field = ""
                for part in error.absolute_path:
                    field += f"[{part}]" if isinstance(part, int) else f".{part}"
                details.append(f"{field.lstrip('.') or '$'}: {error.message}")
            raise ValueError("; ".join(details))
        return ProfileDocument(entry.source, entry.kind, entry.path, data)

    def encode(self, document: ProfileDocument) -> bytes:
        content = (json.dumps(document.data, indent=2, ensure_ascii=False) + "\n"
                   if document.kind == "custom_formats"
                   else yaml.safe_dump(document.data, sort_keys=False, allow_unicode=True))
        return content.encode("utf-8")


def profile_codec() -> YamlJsonCodec:
    schema_dir = Path(__file__).with_name("schemas")
    return YamlJsonCodec({
        kind: json.loads((schema_dir / f"{kind}-v1.json").read_text())
        for kind in ("profiles", "custom_formats")
    })
