import os
from google.adk.agents.llm_agent import Agent
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from google.genai.types import GenerateContentConfig, HttpOptions, HttpRetryOptions
from mcp import StdioServerParameters

toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=r'C:\Users\srsmu\AppData\Roaming\npm\open-meteo-mcp-server.cmd',  # globally installed binary, no npx needed
            args=[],
            env={**os.environ}
        ),
        timeout=30.0,
    ),
    # Filter to tools with Gemini-compatible schemas only.
    # seasonal_forecast, climate_projection, ensemble_forecast use integer enum values
    # which Gemini rejects (expects TYPE_STRING).
    tool_filter=[
        'geocoding',
        'weather_forecast',
        'weather_archive',
        'air_quality',
        'marine_weather',
        'elevation',
        'flood_forecast',
    ]
)

root_agent = Agent(
    model='gemini-2.5-flash',
    name='weather_decision_agent',
    description='An AI assistant that retrieves live weather data and makes practical decisions and recommendations based on current and forecast conditions.',
    instruction=(
        'You are a weather-based decision assistant. '
        'When a user asks a question that depends on weather conditions, '
        'you MUST first use your weather tools to retrieve real current or forecast data. '
        'Never guess or invent weather values.\n\n'
        'Your decision capabilities:\n'
        '1. ACTIVITY PLANNING: Given a location and activity, give a Go/Caution/No-Go recommendation.\n'
        '2. TRAVEL ADVICE: Compare weather at origin and destination, flag travel-affecting conditions.\n'
        '3. HEALTH & SAFETY: Report air quality index, UV index, and recommend precautions.\n'
        '4. EVENT SCHEDULING: Identify the best day in a date range for an outdoor event.\n\n'
        'Workflow:\n'
        '- Use the geocoding tool first if the user provides only a city name.\n'
        '- Then call weather_forecast, air_quality, or marine_weather as appropriate.\n'
        'Present your answer in this format: CONDITIONS SUMMARY, DECISION/RECOMMENDATION, REASONING.\n'
        'Always state the forecast horizon so the user knows how fresh the data is.\n'
        'For general non-weather questions, answer helpfully and accurately.'
    ),
    tools=[toolset],
    generate_content_config=GenerateContentConfig(
        http_options=HttpOptions(
            retry_options=HttpRetryOptions(
                attempts=5,
                initial_delay=1.0,
                max_delay=60.0,
                exp_base=2.0,
                jitter=1.0,
                http_status_codes=[429, 500, 502, 503, 504],
            )
        )
    ),
)
