from __future__ import annotations

from unittest.mock import Mock

import pytest

from warden.arr_service import ArrService
from warden.clients.arr import RadarrClient, SonarrClient


class TestArrService:
    @pytest.fixture()
    def subject(self) -> ArrService:
        return ArrService({"radarr": Mock(spec=RadarrClient), "sonarr": Mock(spec=SonarrClient)})

    @pytest.mark.parametrize("source", ["radarr", "sonarr"])
    async def test_reads_profiles_and_formats_from_selected_client(self, subject: ArrService, source: str) -> None:
        client = subject.clients[source]
        client.list_quality_profiles.return_value = [{"name": "HD"}]
        client.list_custom_formats.return_value = [{"name": "Preferred"}]
        assert await subject.get_profiles(source) == ([{"name": "HD"}], [{"name": "Preferred"}])
        client.list_quality_profiles.assert_awaited_once_with()
        client.list_custom_formats.assert_awaited_once_with()
        other = subject.clients["sonarr" if source == "radarr" else "radarr"]
        other.list_quality_profiles.assert_not_called()
        other.list_custom_formats.assert_not_called()

    async def test_missing_source_has_configuration_error(self, subject: ArrService) -> None:
        subject.clients.clear()
        with pytest.raises(ValueError, match="WARDEN_RADARR_URL and WARDEN_RADARR_API_KEY are required"):
            await subject.get_profiles("radarr")

    async def test_failed_profile_read_does_not_read_formats(self, subject: ArrService) -> None:
        client = subject.clients["radarr"]
        client.list_quality_profiles.side_effect = ValueError("unavailable")
        with pytest.raises(ValueError, match="unavailable"):
            await subject.get_profiles("radarr")
        client.list_custom_formats.assert_not_called()

    async def test_failed_format_read_does_not_return_partial_result(self, subject: ArrService) -> None:
        client = subject.clients["radarr"]
        client.list_custom_formats.side_effect = ValueError("unavailable")
        with pytest.raises(ValueError, match="unavailable"):
            await subject.get_profiles("radarr")
