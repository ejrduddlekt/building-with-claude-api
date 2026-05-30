import concurrent.futures
import html
import json
import re
from pathlib import Path
from statistics import mean
from textwrap import dedent

from anthropic import Anthropic
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# 1. Claude API 기본 설정
# ---------------------------------------------------------------------------

load_dotenv()

client = Anthropic()

# 평가 예제는 여러 번 API를 호출하므로 빠른 Haiku 모델을 사용합니다.
model = "claude-haiku-4-5-20251001"


def add_user_message(messages, text):
    # 사용자가 보낸 메시지를 Claude API 형식으로 대화 기록에 추가합니다.
    user_message = {"role": "user", "content": text}
    messages.append(user_message)


def add_assistant_message(messages, text):
    # Claude가 이미 답변을 시작한 것처럼 assistant 메시지를 미리 넣습니다.
    # JSON만 받을 때 코드블록 시작 부분을 prefill하는 용도로 사용합니다.
    assistant_message = {"role": "assistant", "content": text}
    messages.append(assistant_message)


def chat(messages, system=None, temperature=1.0, stop_sequences=None):
    # Claude API 호출에 필요한 공통 파라미터를 딕셔너리로 만듭니다.
    params = {
        "model": model,
        "max_tokens": 1000,
        "messages": messages,
        "temperature": temperature,
    }

    if system:
        params["system"] = system

    if stop_sequences:
        params["stop_sequences"] = stop_sequences

    message = client.messages.create(**params)

    return message.content[0].text


# ---------------------------------------------------------------------------
# 2. HTML 평가 리포트 생성
# ---------------------------------------------------------------------------

def generate_prompt_evaluation_report(evaluation_results):
    # JSON 결과는 기계가 읽기 좋고, HTML 리포트는 사람이 읽기 좋습니다.
    # 각 테스트 케이스의 입력, 평가 기준, 출력, 점수, reasoning을 표로 보여줍니다.
    total_tests = len(evaluation_results)
    scores = [result["score"] for result in evaluation_results]
    average_score = mean(scores) if scores else 0
    pass_rate = 100 * len([score for score in scores if score >= 7]) / total_tests

    rows = []

    for result in evaluation_results:
        test_case = result["test_case"]

        prompt_inputs_html = "<br>".join(
            [
                f"<strong>{html.escape(key)}:</strong> {html.escape(str(value))}"
                for key, value in test_case["prompt_inputs"].items()
            ]
        )

        criteria_html = "<br>".join(
            [
                f"- {html.escape(str(criterion))}"
                for criterion in test_case["solution_criteria"]
            ]
        )

        score = result["score"]
        if score >= 8:
            score_class = "score-high"
        elif score <= 5:
            score_class = "score-low"
        else:
            score_class = "score-medium"

        rows.append(
            f"""
            <tr>
                <td>{html.escape(test_case["scenario"])}</td>
                <td>{prompt_inputs_html}</td>
                <td>{criteria_html}</td>
                <td class="output"><pre>{html.escape(result["output"])}</pre></td>
                <td><span class="score {score_class}">{score}</span></td>
                <td>{html.escape(result["reasoning"])}</td>
            </tr>
            """
        )

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Prompt Evaluation Report</title>
    <style>
        body {{
            color: #333;
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
        }}
        .header {{
            background-color: #f0f0f0;
            border-radius: 5px;
            margin-bottom: 20px;
            padding: 20px;
        }}
        .summary-stats {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .stat-box {{
            background-color: #fff;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            min-width: 200px;
            padding: 15px;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            margin-top: 5px;
        }}
        table {{
            border-collapse: collapse;
            margin-top: 20px;
            width: 100%;
        }}
        th {{
            background-color: #4a4a4a;
            color: white;
            padding: 12px;
            text-align: left;
        }}
        td {{
            border-bottom: 1px solid #ddd;
            padding: 10px;
            vertical-align: top;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        pre {{
            background-color: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-family: Consolas, Monaco, "Courier New", monospace;
            font-size: 14px;
            margin: 0;
            overflow-x: auto;
            padding: 10px;
            white-space: pre-wrap;
        }}
        .score {{
            border-radius: 3px;
            display: inline-block;
            font-weight: bold;
            padding: 5px 10px;
        }}
        .score-high {{
            background-color: #c8e6c9;
            color: #2e7d32;
        }}
        .score-medium {{
            background-color: #fff9c4;
            color: #f57f17;
        }}
        .score-low {{
            background-color: #ffcdd2;
            color: #c62828;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Prompt Evaluation Report</h1>
        <div class="summary-stats">
            <div class="stat-box">
                <div>Total Test Cases</div>
                <div class="stat-value">{total_tests}</div>
            </div>
            <div class="stat-box">
                <div>Average Score</div>
                <div class="stat-value">{average_score:.1f} / 10</div>
            </div>
            <div class="stat-box">
                <div>Pass Rate (&ge;7)</div>
                <div class="stat-value">{pass_rate:.1f}%</div>
            </div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th>Scenario</th>
                <th>Prompt Inputs</th>
                <th>Solution Criteria</th>
                <th>Output</th>
                <th>Score</th>
                <th>Reasoning</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows)}
        </tbody>
    </table>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# 3. PromptEvaluator
# ---------------------------------------------------------------------------

class PromptEvaluator:
    # 이 클래스는 평가 파이프라인을 한곳에 묶어둔 도구입니다.
    #
    # 역할:
    # 1. 평가용 dataset 생성
    # 2. prompt 실행
    # 3. 모델 기반 채점
    # 4. JSON 결과와 HTML 리포트 저장
    def __init__(self, max_concurrent_tasks=3):
        # 동시에 너무 많은 API 요청을 보내면 rate limit이 날 수 있습니다.
        # 처음에는 1~3 정도로 낮게 시작하는 것이 안전합니다.
        self.max_concurrent_tasks = max_concurrent_tasks

    def render(self, template_string, variables):
        # "{name}" 같은 간단한 placeholder를 variables 값으로 바꿉니다.
        placeholders = re.findall(r"{([^{}]+)}", template_string)

        result = template_string
        for placeholder in placeholders:
            if placeholder in variables:
                result = result.replace(
                    "{" + placeholder + "}", str(variables[placeholder])
                )

        # 프롬프트 안에서 실제 중괄호를 쓰고 싶을 때는 {{ }}로 적습니다.
        return result.replace("{{", "{").replace("}}", "}")

    def generate_unique_ideas(self, task_description, prompt_inputs_spec, num_cases):
        # 먼저 서로 다른 테스트 시나리오 아이디어를 만듭니다.
        prompt_inputs = ""
        for key, value in prompt_inputs_spec.items():
            prompt_inputs += f'"{key}": str # {value}\n'

        prompt = """
Generate {num_cases} unique, diverse ideas for testing a prompt that accomplishes this task:

<task_description>
{task_description}
</task_description>

The prompt will receive the following inputs:
<prompt_inputs>
{prompt_inputs}
</prompt_inputs>

Each idea should represent a distinct scenario or example that tests different aspects of the task.

Output Format:
Provide your response as a structured JSON array where each item is a brief description of the idea.

Example:
```json
[
    "Testing with technical computer science terminology",
    "Testing with medical research findings",
    "Testing with complex mathematical concepts"
]
```

Ensure each idea is:
- Clearly distinct from the others
- Relevant to the task description
- Specific enough to guide generation of a full test case
- Quick to solve without requiring extensive computation
- Solvable with no more than 400 tokens of output

Remember, only generate {num_cases} unique ideas.
"""

        rendered_prompt = self.render(
            dedent(prompt),
            {
                "task_description": task_description,
                "num_cases": num_cases,
                "prompt_inputs": prompt_inputs,
            },
        )

        messages = []
        add_user_message(messages, rendered_prompt)
        add_assistant_message(messages, "```json")

        system_prompt = (
            "You are a test scenario designer specialized in creating diverse, "
            "unique testing scenarios."
        )

        text = chat(
            messages,
            system=system_prompt,
            temperature=1.0,
            stop_sequences=["```"],
        )

        return json.loads(text.strip())

    def generate_test_case(self, task_description, idea, prompt_inputs_spec):
        # 하나의 아이디어를 실제 평가용 test case로 확장합니다.
        example_prompt_inputs = ""
        for key, value in prompt_inputs_spec.items():
            example_prompt_inputs += f'"{key}": "EXAMPLE_VALUE", // {value}\n'

        allowed_keys = ", ".join([f'"{key}"' for key in prompt_inputs_spec.keys()])

        prompt = """
Generate a single detailed test case for a prompt evaluation based on:

<task_description>
{task_description}
</task_description>

<specific_idea>
{idea}
</specific_idea>

<allowed_input_keys>
{allowed_keys}
</allowed_input_keys>

Output Format:
```json
{{
    "prompt_inputs": {{
        {example_prompt_inputs}
    }},
    "solution_criteria": ["criterion 1", "criterion 2"]
}}
```

IMPORTANT REQUIREMENTS:
- You MUST ONLY use these exact input keys in prompt_inputs: {allowed_keys}
- Do NOT add any additional keys to prompt_inputs.
- All keys listed in allowed_input_keys must be included.
- Make the test case realistic and practically useful.
- Include 1 to 4 measurable, concise solution criteria.
- Keep solution criteria focused on the task description and generated inputs.
- Do NOT include any fields beyond the output format.
"""

        rendered_prompt = self.render(
            dedent(prompt),
            {
                "allowed_keys": allowed_keys,
                "task_description": task_description,
                "idea": idea,
                "example_prompt_inputs": example_prompt_inputs,
            },
        )

        messages = []
        add_user_message(messages, rendered_prompt)
        add_assistant_message(messages, "```json")

        system_prompt = (
            "You are a test case creator specializing in designing evaluation "
            "scenarios."
        )

        text = chat(
            messages,
            system=system_prompt,
            temperature=0.7,
            stop_sequences=["```"],
        )

        test_case = json.loads(text.strip())
        test_case["task_description"] = task_description
        test_case["scenario"] = idea

        return test_case

    def generate_dataset(
        self,
        task_description,
        prompt_inputs_spec,
        output_file,
        num_cases=3,
    ):
        # dataset 생성은 2단계입니다.
        # 1. 다양한 scenario idea 생성
        # 2. 각 idea를 prompt_inputs와 solution_criteria가 있는 test case로 변환
        ideas = self.generate_unique_ideas(
            task_description=task_description,
            prompt_inputs_spec=prompt_inputs_spec,
            num_cases=num_cases,
        )

        dataset = []
        completed = 0
        total = len(ideas)

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_concurrent_tasks
        ) as executor:
            future_to_idea = {
                executor.submit(
                    self.generate_test_case,
                    task_description,
                    idea,
                    prompt_inputs_spec,
                ): idea
                for idea in ideas
            }

            for future in concurrent.futures.as_completed(future_to_idea):
                test_case = future.result()
                dataset.append(test_case)

                completed += 1
                print(f"Generated {completed}/{total} test cases")

        output_path = Path(output_file)
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(dataset, file, indent=2)

        return dataset

    def grade_output(self, test_case, output, extra_criteria=None):
        # 모델 채점기는 prompt 결과가 기준을 만족하는지 1~10점으로 평가합니다.
        prompt_inputs = ""
        for key, value in test_case["prompt_inputs"].items():
            prompt_inputs += f'"{key}": "{value}"\n'

        extra_criteria_section = ""
        if extra_criteria:
            extra_criteria_template = """
Mandatory Requirements - ANY VIOLATION MEANS AUTOMATIC FAILURE (score of 3 or lower):
<extra_important_criteria>
{extra_criteria}
</extra_important_criteria>
"""
            extra_criteria_section = self.render(
                dedent(extra_criteria_template),
                {"extra_criteria": extra_criteria},
            )

        eval_template = """
Your task is to evaluate the following AI-generated solution with EXTREME RIGOR.

Original task description:
<task_description>
{task_description}
</task_description>

Original task inputs:
<task_inputs>
{prompt_inputs}
</task_inputs>

Solution to Evaluate:
<solution>
{output}
</solution>

Criteria you should use to evaluate the solution:
<criteria>
{solution_criteria}
</criteria>

{extra_criteria_section}

Scoring Guidelines:
- Score 1-3: Solution fails to meet one or more mandatory requirements.
- Score 4-6: Solution meets mandatory requirements but has significant deficiencies.
- Score 7-8: Solution meets requirements with only minor issues.
- Score 9-10: Solution meets all mandatory and secondary criteria.

IMPORTANT SCORING INSTRUCTIONS:
- Grade the output based ONLY on the listed criteria.
- Do not add your own extra requirements.
- Any violation of a mandatory requirement must result in a score of 3 or lower.

Output Format:
Provide your evaluation as a structured JSON object with these fields:
- "strengths": An array of 1-3 key strengths
- "weaknesses": An array of 1-3 key areas for improvement
- "reasoning": A concise explanation of your assessment
- "score": A number between 1 and 10

Respond with JSON only.
"""

        eval_prompt = self.render(
            dedent(eval_template),
            {
                "task_description": test_case["task_description"],
                "prompt_inputs": prompt_inputs,
                "output": output,
                "solution_criteria": "\n".join(test_case["solution_criteria"]),
                "extra_criteria_section": extra_criteria_section,
            },
        )

        messages = []
        add_user_message(messages, eval_prompt)
        add_assistant_message(messages, "```json")

        eval_text = chat(messages, temperature=0.0, stop_sequences=["```"])

        return json.loads(eval_text.strip())

    def run_test_case(self, test_case, run_prompt_function, extra_criteria=None):
        # 하나의 test case를 실행하고 바로 모델 채점까지 수행합니다.
        output = run_prompt_function(test_case["prompt_inputs"])
        model_grade = self.grade_output(test_case, output, extra_criteria)

        return {
            "output": output,
            "test_case": test_case,
            "score": model_grade["score"],
            "reasoning": model_grade["reasoning"],
            "strengths": model_grade["strengths"],
            "weaknesses": model_grade["weaknesses"],
        }

    def run_evaluation(
        self,
        run_prompt_function,
        dataset_file,
        extra_criteria=None,
        json_output_file="output.json",
        html_output_file="output.html",
    ):
        # dataset 전체에 대해 prompt 실행과 채점을 반복합니다.
        dataset_path = Path(dataset_file)
        with dataset_path.open("r", encoding="utf-8") as file:
            dataset = json.load(file)

        results = []
        completed = 0
        total = len(dataset)

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_concurrent_tasks
        ) as executor:
            future_to_test_case = {
                executor.submit(
                    self.run_test_case,
                    test_case,
                    run_prompt_function,
                    extra_criteria,
                ): test_case
                for test_case in dataset
            }

            for future in concurrent.futures.as_completed(future_to_test_case):
                result = future.result()
                results.append(result)

                completed += 1
                print(f"Graded {completed}/{total} test cases")

        average_score = mean([result["score"] for result in results])
        print(f"Average score: {average_score}")

        json_output_path = Path(json_output_file)
        with json_output_path.open("w", encoding="utf-8") as file:
            json.dump(results, file, indent=2)

        html_output_path = Path(html_output_file)
        report_html = generate_prompt_evaluation_report(results)
        with html_output_path.open("w", encoding="utf-8") as file:
            file.write(report_html)

        return results


# ---------------------------------------------------------------------------
# 4. 이번 강의에서 평가할 초기 prompt
# ---------------------------------------------------------------------------

def run_prompt(prompt_inputs):
    # 첫 시도는 일부러 단순한 prompt로 시작합니다.
    # 점수가 낮게 나와도 괜찮습니다. 이후 강의에서 이 prompt를 하나씩 개선합니다.
    prompt = f"""
What should this person eat?

- Height: {prompt_inputs["height"]}
- Weight: {prompt_inputs["weight"]}
- Goal: {prompt_inputs["goal"]}
- Dietary restrictions: {prompt_inputs["restrictions"]}
"""

    messages = []
    add_user_message(messages, prompt)

    return chat(messages)


# ---------------------------------------------------------------------------
# 5. 전체 실행 흐름
# ---------------------------------------------------------------------------

def run():
    # Section 03의 첫 예제는 "prompt를 개선하기 전 기준점"을 만드는 과정입니다.
    #
    # prompt engineering의 반복 흐름:
    #
    # 1. 목표를 정한다.
    # 2. 초기 prompt를 작성한다.
    # 3. dataset으로 평가한다.
    # 4. 평가 결과를 보고 prompt를 개선한다.
    # 5. 다시 평가한다.
    #
    # 이번 파일은 HTML 리포트까지 생성해서 평가 결과를 눈으로 확인합니다.
    evaluator = PromptEvaluator(max_concurrent_tasks=1)

    base_path = Path(__file__).parent
    dataset_path = base_path / "lesson_01_dataset.json"
    results_path = base_path / "lesson_01_results.json"
    report_path = base_path / "lesson_01_report.html"

    evaluator.generate_dataset(
        task_description="Write a compact, concise 1 day meal plan for a single athlete",
        prompt_inputs_spec={
            "height": "Athlete's height in cm",
            "weight": "Athlete's weight in kg",
            "goal": "Goal of the athlete",
            "restrictions": "Dietary restrictions of the athlete",
        },
        output_file=dataset_path,
        num_cases=3,
    )

    results = evaluator.run_evaluation(
        run_prompt_function=run_prompt,
        dataset_file=dataset_path,
        extra_criteria="""
The output should include:
- Daily caloric total
- Macronutrient breakdown
- Meals with exact foods, portions, and timing
""",
        json_output_file=results_path,
        html_output_file=report_path,
    )

    print()
    print(f"Dataset saved to: {dataset_path}")
    print(f"Results saved to: {results_path}")
    print(f"HTML report saved to: {report_path}")
    print()
    print("Evaluation results:")
    print(json.dumps(results, indent=2))
