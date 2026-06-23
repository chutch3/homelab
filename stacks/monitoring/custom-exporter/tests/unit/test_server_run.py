"""Unit test for run_server — wiring + graceful shutdown (HTTPServer mocked)."""

from http.server import HTTPServer
from unittest.mock import MagicMock, patch

from iperf3_exporter import server


def test_run_server_serves_then_shuts_down_on_keyboard_interrupt():
    fake_httpd = MagicMock(spec=HTTPServer)
    fake_httpd.serve_forever.side_effect = KeyboardInterrupt
    with patch.object(server, "HTTPServer", return_value=fake_httpd) as make_server:
        server.run_server(host="", port=9579, iperf3_path="iperf3")
    make_server.assert_called_once()
    fake_httpd.serve_forever.assert_called_once()
    fake_httpd.shutdown.assert_called_once()  # KeyboardInterrupt → graceful shutdown
