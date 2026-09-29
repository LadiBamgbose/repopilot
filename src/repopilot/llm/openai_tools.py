"""Translate RepoPilot tool schemas into OpenAI Responses API function tools."""

from typing import Any

from repopilot.core.tool_definition import ToolDefinition, tool_schema


def to_openai_function_tool(definition: ToolDefinition) -> dict[str, Any]:
    """Build one OpenAI function tool from a provider-neutral tool schema.

    ``parameters`` is the JSON schema from ``args_model.model_json_schema()``.
    """
    schema = tool_schema(definition)
    return {
        "type": "function",
        "name": schema["name"],
        "description": schema["description"],
        "parameters": schema["parameters"],
    }


def to_openai_function_tools(
    definitions: list[ToolDefinition],
) -> list[dict[str, Any]]:
    """Convert a list of tool definitions into OpenAI function tools."""
    return [to_openai_function_tool(definition) for definition in definitions]
