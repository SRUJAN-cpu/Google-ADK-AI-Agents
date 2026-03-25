from google.adk.agents.llm_agent import Agent
from google.genai.types import GenerateContentConfig, HttpOptions, HttpRetryOptions

root_agent = Agent(
    model='gemini-2.5-flash',
    name='summarization_agent',
    description='An AI assistant specialized in summarizing texts and PDFs.',
    instruction=(
        'You are a summarization assistant. '
        'When the user provides text or asks you to summarize something, '
        'produce a clear, concise summary highlighting the key points. '
        'For general questions, answer helpfully and accurately.'
    ),
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
