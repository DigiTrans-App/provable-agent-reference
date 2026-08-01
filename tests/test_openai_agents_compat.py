from __future__ import annotations

import unittest

from agents import Agent, RunConfig, Runner, function_tool
from pydantic import BaseModel, ConfigDict


class SyntheticOutput(BaseModel):
    """Minimal structured output used only to validate the optional SDK surface."""

    model_config = ConfigDict(extra="forbid")

    text: str


@function_tool
def synthetic_tool() -> str:
    """Return a deterministic value without network access."""

    return "synthetic"


class OpenAIAgentsCompatibilityTests(unittest.TestCase):
    def test_public_sdk_surface_used_by_example_remains_constructible(self) -> None:
        agent = Agent(
            name="SDK compatibility smoke test",
            model="synthetic-model",
            instructions="Return synthetic structured output.",
            tools=[synthetic_tool],
            output_type=SyntheticOutput,
        )
        config = RunConfig(
            tracing_disabled=True,
            trace_include_sensitive_data=False,
            workflow_name="SDK compatibility smoke test",
        )

        self.assertEqual(agent.name, "SDK compatibility smoke test")
        self.assertEqual(agent.model, "synthetic-model")
        self.assertEqual(len(agent.tools), 1)
        self.assertTrue(config.tracing_disabled)
        self.assertFalse(config.trace_include_sensitive_data)
        self.assertEqual(config.workflow_name, "SDK compatibility smoke test")
        self.assertIsNotNone(Runner)


if __name__ == "__main__":
    unittest.main()
