import os
import shutil

import dotenv
dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

import psycopg2

from google.adk.agents.llm_agent import Agent
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from google.genai.types import GenerateContentConfig, HttpOptions, HttpRetryOptions
from mcp import StdioServerParameters

from productivity_assistant.email_tools import send_meeting_invite
from productivity_assistant.calendar_tools import (
    get_current_datetime,
    get_todays_events,
    get_week_events,
    create_calendar_event,
    delete_calendar_event,
)

# ─────────────────────────────────────────────
# Executable paths
# ─────────────────────────────────────────────

_NPX = shutil.which('npx.cmd') or shutil.which('npx') or r'C:\Program Files\nodejs\npx.cmd'
_UVX = shutil.which('uvx') or r'C:\Users\srsmu\.local\bin\uvx.exe'

# ─────────────────────────────────────────────
# Database connection
# Locally: postgresql://localhost/productivity
# Cloud Run: uses Cloud SQL Unix socket via DATABASE_URL env var
# ─────────────────────────────────────────────

_DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://localhost/productivity'   # local dev fallback
)

# ─────────────────────────────────────────────
# Schema initialiser
# Runs at module import — creates tables if they don't exist.
# Uses psycopg2 directly so no MCP dependency at startup.
# ─────────────────────────────────────────────

def _init_schema():
    try:
        conn = psycopg2.connect(_DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id          SERIAL PRIMARY KEY,
                title       TEXT NOT NULL,
                description TEXT,
                status      TEXT DEFAULT 'pending'
                                CHECK(status IN ('pending','in_progress','done','cancelled')),
                priority    TEXT DEFAULT 'medium'
                                CHECK(priority IN ('low','medium','high')),
                due_date    DATE,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS schedules (
                id          SERIAL PRIMARY KEY,
                title       TEXT NOT NULL,
                description TEXT,
                start_time  TIMESTAMPTZ NOT NULL,
                end_time    TIMESTAMPTZ,
                location    TEXT,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS notes (
                id          SERIAL PRIMARY KEY,
                title       TEXT NOT NULL,
                content     TEXT,
                category    TEXT DEFAULT 'general'
                                CHECK(category IN ('general','meeting-prep','daily-log','week-plan')),
                tags        TEXT,
                created_at  TIMESTAMPTZ DEFAULT NOW(),
                updated_at  TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("Schema initialised successfully.")
    except Exception as e:
        print(f"Schema init warning: {e} (tables may already exist)")

_init_schema()

# ─────────────────────────────────────────────
# Shared retry config
# ─────────────────────────────────────────────

_RETRY = GenerateContentConfig(
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
)

# ─────────────────────────────────────────────
# Shared PostgreSQL MCP toolset factory
# Each agent gets its own McpToolset instance (instances are stateful)
# All point to the same Cloud SQL database
# ─────────────────────────────────────────────

def _make_pg_toolset():
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=_NPX,
                args=['-y', '@modelcontextprotocol/server-postgres', _DATABASE_URL],
                env={**os.environ},
            ),
            timeout=30.0,
        ),
        tool_filter=['query'],
    )

# ─────────────────────────────────────────────
# Sub-agent: task_agent
# PostgreSQL → tasks table only
# ─────────────────────────────────────────────

task_agent = Agent(
    model='gemini-2.5-flash',
    name='task_agent',
    description=(
        'Manages tasks: create, update, list, and delete tasks with '
        'priority and due-date tracking stored in PostgreSQL.'
    ),
    instruction=(
        'You are a task management specialist.\n'
        'You operate ONLY on the `tasks` table in PostgreSQL.\n\n'
        'Schema: tasks(id SERIAL, title TEXT, description TEXT, status TEXT, '
        'priority TEXT, due_date DATE, created_at TIMESTAMPTZ)\n'
        '  status values : pending | in_progress | done | cancelled\n'
        '  priority values: low | medium | high\n\n'
        'Rules:\n'
        '1. Call get_current_datetime() first whenever the user uses relative dates '
        '   like "today", "tomorrow", "next week".\n'
        '2. Use the query tool for ALL SQL — SELECT, INSERT, UPDATE, DELETE.\n'
        '3. When listing tasks, ORDER BY priority DESC, due_date ASC NULLS LAST.\n'
        '4. When marking a task done, UPDATE status = \'done\'.\n'
        '5. Never touch the schedules or notes tables.\n'
        '6. Always return a clear human-readable summary of what you did.'
    ),
    tools=[get_current_datetime, _make_pg_toolset()],
    generate_content_config=_RETRY,
)

# ─────────────────────────────────────────────
# Sub-agent: schedule_agent
# PostgreSQL → schedules table only
# ─────────────────────────────────────────────

schedule_agent = Agent(
    model='gemini-2.5-flash',
    name='schedule_agent',
    description=(
        'Manages calendar events: create, list, and query scheduled meetings '
        'and time blocks with start/end times and locations.'
    ),
    instruction=(
        'You are a calendar and schedule specialist.\n'
        'You operate ONLY on the `schedules` table in PostgreSQL.\n\n'
        'Schema: schedules(id SERIAL, title TEXT, description TEXT, '
        'start_time TIMESTAMPTZ, end_time TIMESTAMPTZ, location TEXT, created_at TIMESTAMPTZ)\n\n'
        'Rules:\n'
        '1. Call get_current_datetime() first whenever the user uses relative dates '
        '   like "today", "tomorrow", "next week".\n'
        '2. Use the query tool for ALL SQL.\n'
        '3. Always ORDER BY start_time ASC.\n'
        '4. Never touch the tasks or notes tables.\n'
        '5. Return a clear human-readable summary — include time and location for each event.'
    ),
    tools=[get_current_datetime, _make_pg_toolset()],
    generate_content_config=_RETRY,
)

# ─────────────────────────────────────────────
# Sub-agent: notes_agent
# PostgreSQL → notes table (no filesystem needed — works on Cloud Run)
# ─────────────────────────────────────────────

notes_agent = Agent(
    model='gemini-2.5-flash',
    name='notes_agent',
    description=(
        'Creates, retrieves, and searches notes stored in PostgreSQL. '
        'Used for meeting prep notes, daily logs, and context capture.'
    ),
    instruction=(
        'You are a note-taking and retrieval specialist.\n'
        'You store and retrieve notes in the `notes` table in PostgreSQL.\n\n'
        'Schema: notes(id SERIAL, title TEXT, content TEXT, category TEXT, '
        'tags TEXT, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)\n'
        '  category values: general | meeting-prep | daily-log | week-plan\n\n'
        'Rules:\n'
        '1. Use the query tool for ALL SQL.\n'
        '2. To search notes by keyword: WHERE content ILIKE \'%keyword%\' OR title ILIKE \'%keyword%\'.\n'
        '3. To save a note: INSERT with title, content, category, and tags.\n'
        '4. To update a note: UPDATE content and set updated_at = NOW().\n'
        '5. For daily logs, title should be: Daily Log YYYY-MM-DD.\n'
        '6. For meeting prep, title should be: Meeting Prep - <topic>.\n'
        '7. Never touch the tasks or schedules tables.\n'
        '8. Return a clear summary of what was saved or found.'
    ),
    tools=[_make_pg_toolset()],
    generate_content_config=_RETRY,
)

# ─────────────────────────────────────────────
# Sub-agent: calendar_agent
# Google Calendar API → real calendar fetch + time blocking
# ─────────────────────────────────────────────

calendar_agent = Agent(
    model='gemini-2.5-flash',
    name='calendar_agent',
    description=(
        'READ-ONLY calendar viewer. ONLY use this to show existing Google Calendar events. '
        'NEVER use this to schedule, create, or block time. '
        'For any scheduling or meeting creation, always use email_agent instead.'
    ),
    instruction=(
        'You are a read-only Google Calendar viewer.\n'
        'You can ONLY fetch and display existing calendar events.\n\n'
        'Tools:\n'
        '  get_todays_events() — fetch all events on today\'s calendar\n'
        '  get_week_events()   — fetch all events for the next 7 days\n\n'
        'Rules:\n'
        '1. Use get_todays_events for "today\'s calendar", "what\'s on today".\n'
        '2. Use get_week_events for "this week", "upcoming meetings".\n'
        '3. You CANNOT create, edit, or delete calendar events.\n'
        '   If asked to schedule or block time, tell the user this will be '
        '   handled via email invite instead.\n'
        '4. Return a clear human-readable list of events with title and time.'
    ),
    tools=[get_current_datetime, get_todays_events, get_week_events],
    generate_content_config=_RETRY,
)

# ─────────────────────────────────────────────
# Sub-agent: research_agent
# mcp-server-fetch → fetches web content for meeting prep
# ─────────────────────────────────────────────

_TAVILY_API_KEY = os.getenv('TAVILY_API_KEY', '')

_research_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=_NPX,
            args=['-y', 'tavily-mcp@0.1.4'],
            env={**os.environ, 'TAVILY_API_KEY': _TAVILY_API_KEY},
        ),
        timeout=30.0,
    ),
)

research_agent = Agent(
    model='gemini-2.5-flash',
    name='research_agent',
    description=(
        'Researches topics for meeting preparation by fetching relevant web content '
        'and generating structured talking points and agendas.'
    ),
    instruction=(
        'You are a meeting research specialist.\n'
        'Use the tavily_search tool to research topics for meeting preparation.\n\n'
        'Research strategy:\n'
        '1. Search for the topic using tavily_search.\n'
        '2. Run a second search with "key facts TOPIC" for more depth if needed.\n'
        '3. Synthesize results into a structured meeting prep brief:\n'
        '   ## Background\n'
        '   ## Key Points to Cover\n'
        '   ## Suggested Agenda (with time estimates)\n'
        '   ## Questions to Ask\n'
        '   ## Potential Risks / Watch-outs\n\n'
        'Rules:\n'
        '1. Always search before generating — never rely solely on training knowledge.\n'
        '2. Keep the brief concise — bullet points preferred over long paragraphs.\n'
        '3. Return the full structured brief so it can be saved as a note.'
    ),
    tools=[_research_toolset],
    generate_content_config=_RETRY,
)

# ─────────────────────────────────────────────
# Sub-agent: email_agent
# Sends meeting invite emails with Meet link + Add to Calendar
# ─────────────────────────────────────────────

email_agent = Agent(
    model='gemini-2.5-flash',
    name='email_agent',
    description=(
        'PRIMARY agent for scheduling meetings and blocking time. '
        'Asks for recipient email, meeting details, then sends an invite '
        'with a Google Meet link and Add to Calendar button. '
        'Use this for ANY request to schedule, create, or set up a meeting.'
    ),
    instruction=(
        'You send meeting invite emails on behalf of the user.\n\n'
        'Before calling send_meeting_invite, make sure you have:\n'
        '  1. to_email      — ask the user if not provided\n'
        '  2. meeting_title — the name of the meeting\n'
        '  3. date          — in YYYY-MM-DD format (call get_current_datetime if relative)\n'
        '  4. start_time    — HH:MM in 24h format\n'
        '  5. end_time      — HH:MM in 24h format\n'
        '  6. description   — agenda or notes (optional)\n'
        '  7. location      — meeting link or room (optional)\n\n'
        'Rules:\n'
        '1. Always confirm the details with the user before sending.\n'
        '2. If the user gives a relative date ("tomorrow", "next Monday"), '
        '   call get_current_datetime() first to resolve the actual date.\n'
        '3. After sending, confirm success and share the Google Meet link with the user.'
    ),
    tools=[get_current_datetime, send_meeting_invite],
    generate_content_config=_RETRY,
)

# ─────────────────────────────────────────────
# Root orchestrator agent
# ─────────────────────────────────────────────

root_agent = Agent(
    model='gemini-2.5-flash',
    name='productivity_assistant',
    description=(
        'A multi-agent productivity assistant that coordinates task management, '
        'schedule planning, note-taking, and meeting preparation through '
        'specialized sub-agents backed by Cloud SQL PostgreSQL.'
    ),
    instruction=(
        'You are a personal productivity assistant. '
        'You coordinate five specialists to help the user manage their work.\n\n'
        'YOUR SPECIALISTS:\n'
        '  task_agent     — Task CRUD with priority and due dates (PostgreSQL)\n'
        '  schedule_agent — Internal calendar event management (PostgreSQL)\n'
        '  calendar_agent — Real Google Calendar: fetch events and block time\n'
        '  notes_agent    — Note creation and retrieval (PostgreSQL)\n'
        '  research_agent — Web research for meeting prep\n'
        '  email_agent    — Send meeting invite emails with Meet link + Add to Calendar\n\n'
        'ROUTING RULES:\n'
        '1. Task requests ("add task", "mark done", "what do I need to do") → task_agent\n'
        '2. READ calendar ("what\'s on my calendar", "show my schedule") → calendar_agent\n'
        '3. SCHEDULE / BLOCK TIME ("block my calendar", "schedule a meeting", "set up a call") →\n'
        '   Cannot block calendar directly. Instead:\n'
        '   a. Ask for the recipient email address if not provided\n'
        '   b. Collect meeting details (title, date, time)\n'
        '   c. email_agent — send invite with Meet link + Add to Calendar\n'
        '   d. schedule_agent — save in internal DB\n'
        '4. Note requests ("take a note", "find my notes on X") → notes_agent\n'
        '5. Research requests ("research X", "prep me for my meeting on X") → research_agent\n'
        '6. "Send invite", "email the team", "send meeting details to X" → email_agent\n\n'
        'COMPOUND WORKFLOWS — call sub-agents in sequence, then synthesize:\n\n'
        '"Morning briefing":\n'
        '  1. calendar_agent — fetch today\'s real Google Calendar events\n'
        '  2. task_agent — fetch today\'s pending tasks\n'
        '  3. Synthesize into one morning summary\n\n'
        '"Prep me for [meeting topic]":\n'
        '  1. research_agent — research the topic\n'
        '  2. calendar_agent — check today/week calendar for context\n'
        '  3. notes_agent — save the prep brief\n'
        '  4. task_agent — create a review prep task\n'
        '  5. Summarize everything prepared\n\n'
        '"Block my calendar" / "Schedule a meeting" / "Set up a call":\n'
        '  1. Ask: "What is the meeting title, date, and time?"\n'
        '  2. Ask: "Who should I send the invite to? (email address)"\n'
        '  3. email_agent — send invite with Meet link + Add to Calendar link\n'
        '  4. schedule_agent — save the event in the internal DB\n'
        '  5. Confirm to user: invite sent + Meet link\n\n'
        '"Plan my week":\n'
        '  1. calendar_agent — fetch this week\'s real Google Calendar events\n'
        '  2. task_agent — list all pending tasks\n'
        '  3. notes_agent — save a week plan note\n'
        '  4. Return the full weekly overview\n\n'
        '"End of day wrap-up":\n'
        '  1. task_agent — list done and still-pending tasks\n'
        '  2. notes_agent — save a daily log note\n'
        '  3. Confirm what was logged\n\n'
        'GENERAL RULES:\n'
        '- Synthesize sub-agent results into one clear, well-formatted reply.\n'
        '- Never access the database directly — always delegate.\n'
        '- If intent is ambiguous, ask ONE clarifying question before delegating.\n'
        '- Use markdown formatting in responses (headers, bullets, bold).'
    ),
    sub_agents=[task_agent, schedule_agent, calendar_agent, notes_agent, research_agent, email_agent],
    generate_content_config=_RETRY,
)
