"""Streaming JSON arrays with a bounded single-record buffer."""

import json
from typing import Any, TextIO


class JsonRecords:
    def __init__(self, stream: TextIO, limit: int):
        self.stream = stream
        self.limit = limit
        self.buffer = ""
        self.eof = False

    def refill(self) -> None:
        chunk = self.stream.read(65536)
        self.eof = not chunk
        self.buffer += chunk
        if len(self.buffer) > self.limit:
            raise ValueError("单条数据超过 4 MiB，请将大字段拆为独立文件")

    def token(self) -> str:
        self.buffer = self.buffer.lstrip()
        while not self.buffer and not self.eof:
            self.refill()
            self.buffer = self.buffer.lstrip()
        return self.buffer[:1]

    def consume(self, expected: str) -> None:
        if self.token() != expected:
            raise ValueError("JSON 数据不完整或格式错误")
        self.buffer = self.buffer[1:]

    def record(self) -> dict[str, Any]:
        self.token()
        while True:
            try:
                value, end = json.JSONDecoder().raw_decode(self.buffer)
                break
            except json.JSONDecodeError:
                if self.eof:
                    raise ValueError("JSON 数据不完整或格式错误") from None
                self.refill()
        if not isinstance(value, dict):
            raise ValueError("数据须为包含列名的记录数组")
        self.buffer = self.buffer[end:]
        return value
