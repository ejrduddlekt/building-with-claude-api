import json
from datetime import datetime, timedelta

from anthropic import Anthropic
from anthropic.types import Message, ToolParam
from dotenv import load_dotenv


load_dotenv()

client = Anthropic()
model = "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# 1. Helper functions
# ---------------------------------------------------------------------------

def add_user_message(messages, message):
    user_message = {
        "role": "user",
        "content": message.content if isinstance(message, Message) else message,
    }
    messages.append(user_message)


def add_assistant_message(messages, message):
    assistant_message = {
        "role": "assistant",
        "content": message.content if isinstance(message, Message) else message,
    }
    messages.append(assistant_message)


def chat(messages, system=None, temperature=1.0, stop_sequences=None, tools=None):
    params = {
        "model": model,
        "max_tokens": 1000,
        "messages": messages,
        "temperature": temperature,
    }

    if stop_sequences:
        params["stop_sequences"] = stop_sequences

    if tools:
        params["tools"] = tools

    if system:
        params["system"] = system

    message = client.messages.create(**params)
    return message


def text_from_message(message):
    return "\n".join([block.text for block in message.content if block.type == "text"])


# ---------------------------------------------------------------------------
# 2. Tool functions
# ---------------------------------------------------------------------------

def get_current_datetime(date_format="%Y-%m-%d %H:%M:%S"):
    if not date_format:
        raise ValueError("date_format cannot be empty")

    return datetime.now().strftime(date_format)


def add_duration_to_datetime(
    datetime_str,
    duration=0,
    unit="days",
    input_format="%Y-%m-%d",
):
    date = datetime.strptime(datetime_str, input_format)

    if unit == "seconds":
        new_date = date + timedelta(seconds=duration)
    elif unit == "minutes":
        new_date = date + timedelta(minutes=duration)
    elif unit == "hours":
        new_date = date + timedelta(hours=duration)
    elif unit == "days":
        new_date = date + timedelta(days=duration)
    elif unit == "weeks":
        new_date = date + timedelta(weeks=duration)
    elif unit == "months":
        month = date.month + duration
        year = date.year + month // 12
        month = month % 12
        if month == 0:
            month = 12
            year -= 1

        day = min(
            date.day,
            [
                31,
                29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                31,
                30,
                31,
                30,
                31,
                31,
                30,
                31,
                30,
                31,
            ][month - 1],
        )
        new_date = date.replace(year=year, month=month, day=day)
    elif unit == "years":
        new_date = date.replace(year=date.year + duration)
    else:
        raise ValueError(f"Unsupported time unit: {unit}")

    return new_date.strftime("%A, %B %d, %Y %I:%M:%S %p")


def set_reminder(content, timestamp):
    # 실제 앱이라면 여기서 DB 저장, 알림 예약, 캘린더 연동 등을 수행합니다.
    # 이번 강의에서는 reminder가 설정됐다는 것을 출력만 합니다.
    print(f"----\nSetting the following reminder for {timestamp}:\n{content}\n----")


# ---------------------------------------------------------------------------
# 3. Tool schemas
# ---------------------------------------------------------------------------

get_current_datetime_schema = ToolParam(
    {
        "name": "get_current_datetime",
        "description": (
            "Returns the current date and time formatted according to the specified "
            "format string. This tool provides the current system time formatted as "
            "a string. Use this tool when you need to know the current date and time, "
            "such as for timestamping records, calculating time differences, or "
            "displaying the current time to users."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date_format": {
                    "type": "string",
                    "description": (
                        "A string specifying the format of the returned datetime. "
                        "Uses Python's strftime format codes. For example, "
                        "'%Y-%m-%d' returns just the date in YYYY-MM-DD format, "
                        "'%H:%M:%S' returns just the time in HH:MM:SS format, "
                        "'%B %d, %Y' returns a date like 'May 07, 2025'. "
                        "The default is '%Y-%m-%d %H:%M:%S'."
                    ),
                    "default": "%Y-%m-%d %H:%M:%S",
                }
            },
            "required": [],
        },
    }
)


add_duration_to_datetime_schema = ToolParam(
    {
        "name": "add_duration_to_datetime",
        "description": (
            "Adds a specified duration to a datetime string and returns the resulting "
            "datetime in a detailed format. This tool converts an input datetime "
            "string to a Python datetime object, adds the specified duration in the "
            "requested unit, and returns a formatted string of the resulting datetime."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "datetime_str": {
                    "type": "string",
                    "description": (
                        "The input datetime string to which the duration will be added. "
                        "This should be formatted according to the input_format parameter."
                    ),
                },
                "duration": {
                    "type": "number",
                    "description": (
                        "The amount of time to add to the datetime. Can be positive "
                        "for future dates or negative for past dates. Defaults to 0."
                    ),
                },
                "unit": {
                    "type": "string",
                    "description": (
                        "The unit of time for the duration. Must be one of: seconds, "
                        "minutes, hours, days, weeks, months, or years. Defaults to days."
                    ),
                },
                "input_format": {
                    "type": "string",
                    "description": (
                        "The format string for parsing datetime_str, using Python's "
                        "strptime format codes. For example, '%Y-%m-%d' for dates "
                        "like '2050-01-01'. Defaults to '%Y-%m-%d'."
                    ),
                },
            },
            "required": ["datetime_str"],
        },
    }
)


set_reminder_schema = ToolParam(
    {
        "name": "set_reminder",
        "description": (
            "Creates a timed reminder with the provided content and timestamp. "
            "Use this when a user asks to be reminded about something at a future "
            "date or time."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": (
                        "The message text that should be displayed in the reminder."
                    ),
                },
                "timestamp": {
                    "type": "string",
                    "description": (
                        "The exact date and time when the reminder should trigger, "
                        "formatted as an ISO 8601 timestamp like YYYY-MM-DDTHH:MM:SS."
                    ),
                },
            },
            "required": ["content", "timestamp"],
        },
    }
)


tools = [
    get_current_datetime_schema,
    add_duration_to_datetime_schema,
    set_reminder_schema,
]


# ---------------------------------------------------------------------------
# 4. Tool runner
# ---------------------------------------------------------------------------

def run_tool(tool_name, tool_input):
    # 새 도구를 추가할 때의 핵심 패턴:
    #
    # 1. tool function 작성
    # 2. tool schema 작성
    # 3. tools 목록에 schema 추가
    # 4. run_tool에 name -> function 매핑 추가
    if tool_name == "get_current_datetime":
        return get_current_datetime(**tool_input)
    elif tool_name == "add_duration_to_datetime":
        return add_duration_to_datetime(**tool_input)
    elif tool_name == "set_reminder":
        return set_reminder(**tool_input)

    raise ValueError(f"Unknown tool: {tool_name}")


def run_tools(message):
    tool_requests = [block for block in message.content if block.type == "tool_use"]
    tool_result_blocks = []

    for tool_request in tool_requests:
        try:
            tool_output = run_tool(tool_request.name, tool_request.input)
            tool_result_block = {
                "type": "tool_result",
                "tool_use_id": tool_request.id,
                "content": json.dumps(tool_output),
                "is_error": False,
            }
        except Exception as error:
            tool_result_block = {
                "type": "tool_result",
                "tool_use_id": tool_request.id,
                "content": f"Error: {error}",
                "is_error": True,
            }

        tool_result_blocks.append(tool_result_block)

    return tool_result_blocks


# ---------------------------------------------------------------------------
# 5. Conversation loop
# ---------------------------------------------------------------------------

def run_conversation(messages):
    while True:
        response = chat(messages, tools=tools)

        add_assistant_message(messages, response)
        print(text_from_message(response))

        if response.stop_reason != "tool_use":
            break

        tool_results = run_tools(response)
        add_user_message(messages, tool_results)

    return messages


def run():
    # 이 요청은 두 도구가 순서대로 필요합니다.
    #
    # 1. add_duration_to_datetime:
    #    2050-01-01에서 177일 뒤 날짜 계산
    #
    # 2. set_reminder:
    #    계산된 날짜에 doctor's appointment reminder 설정
    messages = []
    add_user_message(
        messages,
        "Set a reminder for my doctors appointment. Its 177 days after Jan 1st, 2050.",
    )

    final_messages = run_conversation(messages)

    print()
    print("Full conversation history:")
    print(final_messages)
