import pytest

from agent.agent import TravelAgent
from agent.task import sampleTask
from recorder.recorder import TraceRecorder


@pytest.fixture
def task():
    return sampleTask()


@pytest.fixture
def make_trace(tmp_path, task):
    """Run the agent into tmp_path and return (trace, traces_dir)."""

    def _make(fault_type=None, root_cause_step_id=None, defects=None):
        recorder = TraceRecorder(task=task, base_dir=str(tmp_path))
        fault_config = None
        if fault_type:
            fault_config = {"fault_type": fault_type, "root_cause_step_id": root_cause_step_id}
            recorder.trace["ground_truth"] = {
                "failure_type": fault_type,
                "root_cause_step_id": root_cause_step_id,
                "notes": "test",
            }
        trace = TravelAgent(
            task=task, recorder=recorder, fault_config=fault_config, defects=defects
        ).run()
        return trace, str(tmp_path)

    return _make
