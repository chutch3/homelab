"""Unit tests for the __main__ entry point (arg parsing + run_server wiring)."""

import sys

import pytest

from iperf3_exporter import __main__


def test_main_passes_parsed_args_to_run_server(monkeypatch):
    captured = {}
    monkeypatch.setattr(__main__, "run_server", lambda **kw: captured.update(kw))
    monkeypatch.setattr(
        sys, "argv",
        ["iperf3-exporter", "--host", "10.0.0.1", "--port", "9999", "--iperf3-path", "/usr/bin/iperf3"],
    )
    __main__.main()
    assert captured == {"host": "10.0.0.1", "port": 9999, "iperf3_path": "/usr/bin/iperf3"}


def test_main_uses_defaults(monkeypatch):
    captured = {}
    monkeypatch.setattr(__main__, "run_server", lambda **kw: captured.update(kw))
    monkeypatch.setattr(sys, "argv", ["iperf3-exporter"])
    __main__.main()
    assert captured == {"host": "", "port": 9579, "iperf3_path": "iperf3"}


def test_main_exits_1_when_run_server_raises(monkeypatch, capsys):
    def boom(**kw):
        raise RuntimeError("server boom")

    monkeypatch.setattr(__main__, "run_server", boom)
    monkeypatch.setattr(sys, "argv", ["iperf3-exporter"])
    with pytest.raises(SystemExit) as exc:
        __main__.main()
    assert exc.value.code == 1
    assert "Error: server boom" in capsys.readouterr().err
