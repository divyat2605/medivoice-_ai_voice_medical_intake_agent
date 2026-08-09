"""Entry point: `python main.py dev` starts the LiveKit agent worker."""

from agent import entrypoint
from livekit.agents import WorkerOptions, cli

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
