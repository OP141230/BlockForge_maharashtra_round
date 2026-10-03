from agent.task import sampleTask
from agent.agent import TravelAgent
from recorder.recorder import TraceRecorder


def main() -> None:
    task = sampleTask()

    recorder = TraceRecorder(task=task)

    agent = TravelAgent(
        task=task,
        recorder=recorder,
    )

    trace = agent.run()

    print("Black Box Phase 1 run complete.")
    print(f"Trace ID: {trace['trace_id']}")
    print(f"Status: {trace['status']}")
    print(f"Saved to: {recorder.trace_dir}")


if __name__ == "__main__":
    main()