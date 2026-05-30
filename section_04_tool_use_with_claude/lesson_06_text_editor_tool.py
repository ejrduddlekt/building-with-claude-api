import json
import shutil
from pathlib import Path

from anthropic import Anthropic
from anthropic.types import Message
from dotenv import load_dotenv


load_dotenv()

client = Anthropic()
model = "claude-sonnet-4-5-20250929"

# 이 파일에서 가장 중요한 전체 흐름:
#
# 사용자: "main.py를 열고 요약해줘"
#   ↓
# Python 앱: Claude에게 질문 + built-in text editor schema stub 전송
#   ↓
# Claude: tool_use block으로 view 명령 요청
#   {
#       "name": "str_replace_based_edit_tool",
#       "input": {
#           "command": "view",
#           "path": "./main.py"
#       }
#   }
#   ↓
# Python 앱: TextEditorTool.view("./main.py") 실제 실행
#   ↓
# Python 앱: 파일 내용을 tool_result block으로 Claude에게 전달
#   ↓
# Claude: 파일 내용을 읽고 최종 요약 답변 생성
#
# 핵심:
# Claude는 "어떤 파일 명령을 실행할지" 판단합니다.
# Python 앱은 "실제 파일 시스템 작업"을 수행합니다.


# ---------------------------------------------------------------------------
# 1. Helper functions
# ---------------------------------------------------------------------------

def add_user_message(messages, message):
    # Claude API는 이전 대화를 자동으로 기억하지 않습니다.
    # 따라서 user 메시지를 messages 리스트에 직접 추가합니다.
    #
    # message는 두 가지 형태가 들어올 수 있습니다.
    # 1. 사용자가 작성한 일반 문자열
    # 2. tool 실행 결과가 담긴 block list
    #
    # Message 객체가 들어오면 content 부분만 꺼내 저장합니다.
    user_message = {
        "role": "user",
        "content": message.content if isinstance(message, Message) else message,
    }
    messages.append(user_message)


def add_assistant_message(messages, message):
    # Claude가 보낸 assistant 응답도 직접 messages에 추가합니다.
    #
    # assistant 응답에는 일반 텍스트뿐 아니라 tool_use block이 들어갈 수 있습니다.
    # 그래서 text만 꺼내지 않고 message.content 전체를 저장합니다.
    assistant_message = {
        "role": "assistant",
        "content": message.content if isinstance(message, Message) else message,
    }
    messages.append(assistant_message)


def chat(messages, system=None, temperature=1.0, stop_sequences=None, tools=None):
    # 지금까지 쌓인 messages 전체를 Claude에게 보냅니다.
    #
    # tools에 get_text_edit_schema()를 넣으면 Claude가 text editor tool을 사용할 수 있습니다.
    # 함수 실행 결과로 text만 반환하지 않고 Message 객체 전체를 반환합니다.
    # 이유: 이후 코드에서 response.stop_reason과 tool_use block을 확인해야 하기 때문입니다.
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
    # Claude 응답에는 TextBlock과 ToolUseBlock이 함께 들어갈 수 있습니다.
    #
    # 터미널에 출력할 때는 사람이 읽을 수 있는 TextBlock만 골라냅니다.
    # tool_use block은 run_tools()에서 별도로 처리합니다.
    return "\n".join([block.text for block in message.content if block.type == "text"])


# ---------------------------------------------------------------------------
# 2. Text editor implementation
# ---------------------------------------------------------------------------

class TextEditorTool:
    # Claude already knows the text editor schema.
    #
    # 하지만 Claude API 서버는 우리 컴퓨터의 파일을 직접 읽거나 수정할 수 없습니다.
    # 따라서 view, str_replace, create, insert 명령을 실제로 실행할 Python 코드가 필요합니다.
    def __init__(self, base_dir=None, backup_dir=None):
        # base_dir:
        # Claude가 접근할 수 있는 최상위 폴더입니다.
        # 기본값은 현재 Python 프로그램을 실행한 폴더입니다.
        #
        # 예:
        # base_dir = D:\Develop\Claude\Building-with-claude-api
        #
        # Claude가 "./main.py"를 요청하면 실제 경로는:
        # D:\Develop\Claude\Building-with-claude-api\main.py
        #
        # backup_dir:
        # 파일 수정 전에 원본을 백업하는 폴더입니다.
        self.base_dir = Path(base_dir or Path.cwd()).resolve()
        self.backup_dir = Path(
            backup_dir or self.base_dir / ".text_editor_backups"
        ).resolve()

    def _validate_path(self, file_path):
        # 모든 파일 작업 전에 반드시 호출하는 보안 검사입니다.
        #
        # Claude가 "../../../secret.txt" 같은 경로를 요청하면
        # base_dir 바깥 파일에 접근할 수 있습니다.
        # resolve()로 실제 절대 경로를 만든 뒤 relative_to()로 base_dir 내부인지 검사합니다.
        path = (self.base_dir / file_path).resolve()

        try:
            path.relative_to(self.base_dir)
        except ValueError as error:
            raise ValueError(
                f"Access denied: Path '{file_path}' is outside the allowed directory"
            ) from error

        return path

    def _backup_file(self, file_path):
        # 수정 전 원본 파일을 백업합니다.
        # 현재 Claude 4 text editor schema에는 undo_edit 명령이 없지만,
        # 애플리케이션 차원에서 복구할 수 있도록 백업은 남겨둡니다.
        if not file_path.exists():
            return

        self.backup_dir.mkdir(parents=True, exist_ok=True)

        backup_path = self.backup_dir / f"{file_path.name}.bak"
        shutil.copy2(file_path, backup_path)

    def view(self, file_path, view_range=None):
        # command == "view"일 때 실행됩니다.
        #
        # file_path가 폴더면:
        #   폴더 안의 파일 이름 목록 반환
        #
        # file_path가 파일이면:
        #   파일 내용을 줄 번호와 함께 반환
        #
        # view_range가 [2, 5]라면:
        #   파일 전체가 아니라 2~5번째 줄만 반환
        path = self._validate_path(file_path)

        if path.is_dir():
            # 디렉터리를 view하면 내부 파일 이름 목록을 보여줍니다.
            return "\n".join(sorted(item.name for item in path.iterdir()))

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = path.read_text(encoding="utf-8")
        lines = content.splitlines()

        if view_range:
            # Claude가 특정 줄만 읽고 싶을 때 사용하는 옵션입니다.
            # line number는 사람이 읽는 방식과 맞추기 위해 1부터 시작합니다.
            start, end = view_range
            if start < 1:
                raise ValueError("view_range start line must be 1 or greater")

            if end == -1:
                end = len(lines)

            lines = lines[start - 1 : end]
            first_line_number = start
        else:
            first_line_number = 1

        return "\n".join(
            [
                f"{line_number}: {line}"
                for line_number, line in enumerate(lines, first_line_number)
            ]
        )

    def str_replace(self, file_path, old_str, new_str):
        # command == "str_replace"일 때 실행됩니다.
        #
        # 파일 안에서 old_str을 찾아 new_str로 바꿉니다.
        # 안전을 위해 정확히 한 곳에서만 old_str이 발견되어야 합니다.
        #
        # 0개 발견:
        #   교체할 위치를 찾지 못했으므로 에러
        #
        # 2개 이상 발견:
        #   어느 위치를 바꿔야 하는지 애매하므로 에러
        #
        # 1개 발견:
        #   백업 후 교체
        path = self._validate_path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = path.read_text(encoding="utf-8")
        match_count = content.count(old_str)

        if match_count == 0:
            raise ValueError(
                "No match found for replacement. Check the old text and try again."
            )

        if match_count > 1:
            raise ValueError(
                f"Found {match_count} matches. Include more context to make the match unique."
            )

        self._backup_file(path)
        path.write_text(content.replace(old_str, new_str), encoding="utf-8")

        return "Successfully replaced text at exactly one location."

    def create(self, file_path, file_text):
        # command == "create"일 때 실행됩니다.
        #
        # 새 파일을 만듭니다.
        # 이미 파일이 있으면 덮어쓰지 않고 에러를 냅니다.
        # 기존 파일 수정은 str_replace를 사용해야 합니다.
        path = self._validate_path(file_path)

        if path.exists():
            raise FileExistsError(
                "File already exists. Use str_replace to modify the existing file."
            )

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(file_text, encoding="utf-8")

        return f"Successfully created {file_path}"

    def insert(self, file_path, insert_line, insert_text):
        # command == "insert"일 때 실행됩니다.
        #
        # 특정 줄 뒤에 새 텍스트를 삽입합니다.
        #
        # insert_line == 0:
        #   파일 맨 앞에 삽입
        #
        # insert_line == 3:
        #   기존 3번째 줄 뒤에 삽입
        path = self._validate_path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        lines = path.read_text(encoding="utf-8").splitlines()

        if insert_line < 0 or insert_line > len(lines):
            raise IndexError(
                f"Line number {insert_line} is out of range. File has {len(lines)} lines."
            )

        self._backup_file(path)
        lines.insert(insert_line, insert_text)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        return f"Successfully inserted text after line {insert_line}"


# ---------------------------------------------------------------------------
# 3. Built-in schema stub and tool routing
# ---------------------------------------------------------------------------

def get_text_edit_schema():
    # 일반 tool은 name, description, input_schema를 직접 작성했습니다.
    #
    # Text editor tool은 schema가 Claude 모델 안에 내장되어 있습니다.
    # 그래서 Claude 4 계열에서는 아래 작은 stub만 보내면 됩니다.
    #
    # 일반 tool:
    # {
    #     "name": "...",
    #     "description": "...",
    #     "input_schema": {...}
    # }
    #
    # built-in text editor tool:
    # {
    #     "type": "text_editor_20250728",
    #     "name": "str_replace_based_edit_tool"
    # }
    #
    # Claude는 type 값을 보고 내장된 전체 schema를 자동으로 사용합니다.
    return {
        "type": "text_editor_20250728",
        "name": "str_replace_based_edit_tool",
        "max_characters": 10000,
    }


# TextEditorTool 객체를 하나 생성합니다.
# 이후 모든 view/create/replace/insert 요청은 이 객체를 통해 실행됩니다.
text_editor_tool = TextEditorTool()


def run_tool(tool_name, tool_input):
    # Claude가 반환한 tool_use block 예시:
    #
    # {
    #     "name": "str_replace_based_edit_tool",
    #     "input": {
    #         "command": "view",
    #         "path": "./main.py"
    #     }
    # }
    #
    # name으로 text editor 요청인지 확인하고,
    # input 안의 command 값으로 실제 Python 메서드를 선택합니다.
    if tool_name != "str_replace_based_edit_tool":
        raise ValueError(f"Unknown tool name: {tool_name}")

    command = tool_input["command"]

    if command == "view":
        return text_editor_tool.view(
            tool_input["path"],
            tool_input.get("view_range"),
        )
    elif command == "str_replace":
        return text_editor_tool.str_replace(
            tool_input["path"],
            tool_input["old_str"],
            tool_input["new_str"],
        )
    elif command == "create":
        return text_editor_tool.create(
            tool_input["path"],
            tool_input["file_text"],
        )
    elif command == "insert":
        return text_editor_tool.insert(
            tool_input["path"],
            tool_input["insert_line"],
            tool_input["insert_text"],
        )

    raise ValueError(f"Unknown text editor command: {command}")


def run_tools(message):
    # 하나의 Claude 응답에는 여러 tool_use block이 있을 수 있습니다.
    #
    # 예:
    # 1. main.py 읽기
    # 2. test.py 읽기
    #
    # 그래서 모든 tool_use block을 찾아 순서대로 실행하고,
    # 각각의 결과를 tool_result_blocks 리스트에 넣습니다.
    tool_requests = [block for block in message.content if block.type == "tool_use"]
    tool_result_blocks = []

    for tool_request in tool_requests:
        try:
            # Claude가 요청한 파일 작업을 실제로 실행합니다.
            tool_output = run_tool(tool_request.name, tool_request.input)

            # 성공 결과를 Claude API가 요구하는 tool_result 형식으로 만듭니다.
            #
            # tool_use_id:
            # 어떤 tool_use 요청에 대한 결과인지 연결하는 번호표입니다.
            tool_result_block = {
                "type": "tool_result",
                "tool_use_id": tool_request.id,
                "content": json.dumps(tool_output),
                "is_error": False,
            }
        except Exception as error:
            # 실패해도 Claude에게 에러 결과를 돌려줍니다.
            #
            # is_error=True를 받은 Claude는:
            # - 경로를 다시 확인하거나
            # - 더 구체적인 old_str을 보내거나
            # - 다른 명령을 선택할 수 있습니다.
            tool_result_block = {
                "type": "tool_result",
                "tool_use_id": tool_request.id,
                "content": f"Error: {error}",
                "is_error": True,
            }

        tool_result_blocks.append(tool_result_block)

    return tool_result_blocks


# ---------------------------------------------------------------------------
# 4. Conversation loop
# ---------------------------------------------------------------------------

def run_conversation(messages):
    # 이전 lesson과 같은 conversation loop입니다.
    #
    # 차이점:
    # 직접 만든 JSON schema 대신 built-in text editor schema stub을 넘깁니다.
    # Claude가 view, str_replace, create, insert 명령을 선택하면
    # run_tool()이 실제 파일 작업을 수행합니다.
    #
    # while loop 한 바퀴:
    #
    # 1. messages + schema stub을 Claude에게 보냄
    # 2. assistant 응답 전체를 messages에 저장
    # 3. stop_reason 확인
    # 4. tool_use면 실제 파일 작업 실행
    # 5. tool_result를 user 메시지로 저장
    # 6. 다시 Claude에게 보내기
    #
    # Claude가 더 이상 tool을 요청하지 않으면 최종 자연어 답변이 준비된 상태입니다.
    while True:
        # Claude에게 지금까지의 대화와 text editor 도구 정보를 전달합니다.
        response = chat(
            messages,
            tools=[get_text_edit_schema()],
        )

        # Claude가 보낸 text/tool_use block 전체를 대화 기록에 저장합니다.
        add_assistant_message(messages, response)

        # 중간 설명 또는 최종 답변이 있으면 터미널에 출력합니다.
        print(text_from_message(response))

        # tool_use가 아니면 더 실행할 파일 작업이 없다는 뜻입니다.
        if response.stop_reason != "tool_use":
            break

        # Claude가 요청한 view/create/replace/insert 명령을 실제로 실행합니다.
        tool_results = run_tools(response)

        # 실행 결과를 user 역할의 tool_result 메시지로 대화 기록에 추가합니다.
        # 다음 loop에서 Claude가 이 결과를 읽습니다.
        add_user_message(messages, tool_results)

    return messages


def run():
    # 첫 실행은 읽기 전용 요청으로 시작합니다.
    # Claude는 text editor의 view 명령으로 main.py를 읽고 요약합니다.
    #
    # 파일 수정 기능도 구현되어 있지만, 자동 실행 예제에서는 저장소 파일을 변경하지 않습니다.
    #
    # 예상 흐름:
    #
    # 1. Claude -> view("./main.py") 요청
    # 2. Python -> main.py 내용을 읽어서 반환
    # 3. Claude -> main.py 요약 답변
    messages = []
    add_user_message(
        messages,
        "Open the ./main.py file with the text editor tool and summarize its contents. Do not modify any files.",
    )

    run_conversation(messages)
