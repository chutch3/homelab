import pytest

from warden.models import InstanceWanted, WantKind
from warden.services.planner import HuntPlanner
from tests.factories import wanted_item


class TestHuntPlanner:
    @pytest.fixture()
    def subject(self) -> HuntPlanner:
        return HuntPlanner()

    def test_caps_at_allowance(self, subject: HuntPlanner):
        wanted = {
            "radarr": InstanceWanted(
                missing=tuple(wanted_item("radarr", i) for i in range(10)),
                cutoff_unmet=(),
            )
        }
        selected = subject.plan(allowance=3, wanted=wanted)
        assert len(selected) == 3

    def test_missing_selected_before_cutoff(self, subject: HuntPlanner):
        wanted = {
            "radarr": InstanceWanted(
                missing=(wanted_item("radarr", 1),),
                cutoff_unmet=(wanted_item("radarr", 2, WantKind.CUTOFF_UNMET),),
            )
        }
        selected = subject.plan(allowance=1, wanted=wanted)
        assert selected == [wanted_item("radarr", 1)]

    def test_round_robins_across_instances(self, subject: HuntPlanner):
        wanted = {
            "radarr": InstanceWanted(missing=(wanted_item("radarr", 1), wanted_item("radarr", 2)),
                                     cutoff_unmet=()),
            "sonarr": InstanceWanted(missing=(wanted_item("sonarr", 9),), cutoff_unmet=()),
        }
        selected = subject.plan(allowance=2, wanted=wanted)
        assert [s.instance for s in selected] == ["radarr", "sonarr"]

    def test_zero_allowance_selects_nothing(self, subject: HuntPlanner):
        wanted = {"radarr": InstanceWanted(missing=(wanted_item("radarr", 1),), cutoff_unmet=())}
        assert subject.plan(allowance=0, wanted=wanted) == []
