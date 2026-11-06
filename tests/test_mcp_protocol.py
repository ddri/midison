"""
End-to-end MCP protocol tests over real stdio.

These launch the server as a subprocess and speak raw newline-delimited
JSON-RPC to it, exactly as Claude Desktop does. They deliberately avoid the MCP
SDK's client API so the same tests judge the server under any SDK major
version: they pin wire behaviour, not SDK internals.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROTOCOL_VERSION = "2025-06-18"
EXPECTED_TOOLS = {
    "generate_midi_progression",
    "get_ableton_session_state",
    "send_to_ableton",
    "stream_to_midi_port",
    "install_ableton_integrations",
    "set_output_directory",
    "suggest_next_chord",
    "generate_song_structure",
    "list_vibes",
}


class StdioClient:
    def __init__(self, home: Path):
        env = {**os.environ, "HOME": str(home)}
        self.proc = subprocess.Popen(  # nosec B603 - fixed argv, test only
            [sys.executable, "-m", "midison.mcp_server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            env=env,
        )
        self._next_id = 0

    def request(self, method: str, params: dict | None = None) -> dict:
        self._next_id += 1
        msg = {"jsonrpc": "2.0", "id": self._next_id, "method": method}
        if params is not None:
            msg["params"] = params
        self._send(msg)
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError(f"server closed stdout during {method}")
            reply = json.loads(line)
            if reply.get("id") == self._next_id:
                return reply

    def notify(self, method: str) -> None:
        self._send({"jsonrpc": "2.0", "method": method})

    def _send(self, msg: dict) -> None:
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def close(self) -> None:
        self.proc.stdin.close()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()


@pytest.fixture
def client(tmp_path):
    c = StdioClient(tmp_path)
    init = c.request(
        "initialize",
        {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "midison-tests", "version": "0"},
        },
    )
    c.init_result = init["result"]
    c.notify("notifications/initialized")
    yield c
    c.close()


def call(client: StdioClient, name: str, arguments: dict) -> dict:
    reply = client.request("tools/call", {"name": name, "arguments": arguments})
    assert "error" not in reply, reply
    return reply["result"]


def test_initialize_identifies_server_and_tools_capability(client):
    assert client.init_result["serverInfo"]["name"] == "midison"
    assert "tools" in client.init_result["capabilities"]


def test_tools_list_returns_every_tool_with_schema(client):
    tools = client.request("tools/list")["result"]["tools"]
    assert {t["name"] for t in tools} == EXPECTED_TOOLS
    for t in tools:
        assert t["description"]
        assert t["inputSchema"]["type"] == "object"


def test_successful_call_returns_json_text(client):
    result = call(client, "suggest_next_chord", {"current_progression": "ii7 - V7"})
    assert not result.get("isError")
    assert result["content"][0]["type"] == "text"
    payload = json.loads(result["content"][0]["text"])
    assert payload["suggestions"]


def test_generate_writes_midi_end_to_end(client, tmp_path):
    result = call(
        client,
        "generate_midi_progression",
        {
            "key_center": "C",
            "scale_type": "major",
            "bpm": 100,
            "chords": [
                {"numeral": n, "duration_beats": 4} for n in ("ii7", "V7", "Imaj7")
            ],
        },
    )
    assert not result.get("isError"), result
    payload = json.loads(result["content"][0]["text"])
    midi = Path(payload["filepath"])
    assert midi.exists()
    assert midi.is_relative_to(tmp_path)


def test_schema_violation_is_a_tool_error_not_a_protocol_error(client):
    result = call(client, "suggest_next_chord", {})
    assert result["isError"] is True
    assert result["content"][0]["text"].startswith("Input validation error:")
    assert "current_progression" in result["content"][0]["text"]


def test_unknown_tool_is_a_tool_error(client):
    result = call(client, "nonexistent", {})
    assert result["isError"] is True
    assert "Unknown tool: nonexistent" in result["content"][0]["text"]


def test_handler_exception_is_a_tool_error_with_message(client):
    result = call(
        client,
        "generate_midi_progression",
        {
            "key_center": "C",
            "scale_type": "major",
            "bpm": 100,
            "chords": [{"numeral": "not-a-numeral", "duration_beats": 4}],
        },
    )
    assert result["isError"] is True
    text = result["content"][0]["text"]
    assert text
    # Must come from the handler, not the schema check.
    assert not text.startswith("Input validation error")


def test_server_survives_errors(client):
    call(client, "nonexistent", {})
    call(client, "suggest_next_chord", {})
    result = call(client, "list_vibes", {})
    assert not result.get("isError")
