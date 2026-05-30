# Section 02. Prompt Evaluation

## 1. Prompt Evaluation의 목적

프롬프트 평가는 프롬프트가 얼마나 잘 동작하는지 객관적으로 확인하는 과정이다.

나쁜 방식:

```text
프롬프트 한두 번 실행
→ 괜찮아 보이면 사용
```

좋은 방식:

```text
테스트 데이터셋 생성
→ 여러 입력으로 프롬프트 실행
→ 결과 채점
→ 평균 점수 확인
→ 프롬프트 개선
→ 다시 평가
```

핵심은 “느낌”이 아니라 점수로 비교하는 것이다.

## 2. 기본 평가 워크플로

평가 파이프라인은 보통 3단계로 나뉜다.

```text
dataset
→ run_prompt(test_case)
→ run_test_case(test_case)
→ run_eval(dataset)
```

### run_prompt

테스트 케이스를 실제 프롬프트에 넣고 Claude에게 보낸다.

```python
def run_prompt(test_case):
    prompt = f"""
Please solve the following task:

{test_case["task"]}
"""
    messages = []
    add_user_message(messages, prompt)
    return chat(messages)
```

### run_test_case

하나의 테스트 케이스를 실행하고 결과를 딕셔너리로 묶는다.

```python
def run_test_case(test_case):
    output = run_prompt(test_case)
    score = 10

    return {
        "output": output,
        "test_case": test_case,
        "score": score,
    }
```

처음에는 점수를 하드코딩해도 된다. 전체 파이프라인이 돌아가는지 확인하는 목적이다.

### run_eval

데이터셋 전체를 반복 실행한다.

```python
def run_eval(dataset):
    results = []

    for test_case in dataset:
        result = run_test_case(test_case)
        results.append(result)

    return results
```

## 3. Dataset 생성

데이터셋은 평가할 입력 목록이다.

기본 구조:

```json
[
  {
    "task": "Create a JSON object for an AWS IAM policy"
  }
]
```

코드 채점까지 하려면 `format`이 필요하다.

```json
{
  "task": "Create a JSON object for an AWS IAM policy",
  "format": "json"
}
```

완성형 평가에서는 `solution_criteria`도 추가한다.

```json
{
  "task": "Create a JSON object for an AWS IAM policy",
  "format": "json",
  "solution_criteria": "Must include Version, Statement, Effect, Action, Resource..."
}
```

## 4. Dataset 저장

Python 데이터를 JSON 파일로 저장:

```python
with output_path.open("w", encoding="utf-8") as file:
    json.dump(dataset, file, indent=2)
```

의미:

- `"w"`: 쓰기 모드
- `encoding="utf-8"`: 한글/특수문자 안전하게 저장
- `json.dump(...)`: Python 리스트/딕셔너리를 JSON 파일로 저장
- `indent=2`: 보기 좋게 들여쓰기

JSON 파일 읽기:

```python
with dataset_path.open("r", encoding="utf-8") as file:
    dataset = json.load(file)
```

`json.load(...)`는 JSON 파일 내용을 Python 데이터로 바꾼다.

## 5. Grader 종류

### Code Grader

코드로 자동 검사한다.

예:

- JSON 문법이 맞는지
- Python 문법이 맞는지
- Regex 문법이 맞는지
- 특정 단어가 있는지
- 길이가 적절한지

장점: 빠르고 명확하다.  
단점: 의미 품질 판단은 어렵다.

### Model Grader

다른 AI 모델에게 결과를 평가하게 한다.

잘 보는 것:

- 과제를 제대로 따랐는지
- 답변 품질
- 완성도
- 정확성
- 유용성

장점: 유연하다.  
단점: 완전히 일관적이지 않을 수 있다.

### Human Grader

사람이 직접 평가한다.

장점: 가장 유연하고 섬세하다.  
단점: 느리고 귀찮고 비용이 든다.

## 6. Model Based Grading

모델 채점기는 Claude의 출력 결과를 다시 Claude에게 보내 점수를 받는 방식이다.

흐름:

```text
1차 Claude 호출: task 해결
2차 Claude 호출: 결과 평가
```

모델 채점 함수:

```python
def grade_by_model(test_case, output):
    eval_prompt = f"""
You are an expert AWS code reviewer.

Original Task:
{test_case["task"]}

Solution to Evaluate:
{output}

Return JSON with strengths, weaknesses, reasoning, score.
"""

    messages = []
    add_user_message(messages, eval_prompt)
    add_assistant_message(messages, "```json")
    eval_text = chat(messages, stop_sequences=["```"])

    return json.loads(eval_text.strip())
```

점수만 요청하지 말고 다음을 함께 요청하는 것이 중요하다.

- `strengths`
- `weaknesses`
- `reasoning`
- `score`

이유: 점수만 달라고 하면 모델이 애매한 중간 점수를 주는 경향이 있다.

## 7. Code Based Grading

코드 기반 채점은 생성된 출력이 실제로 해당 형식의 문법을 만족하는지 검사한다.

JSON 검사:

```python
def validate_json(text):
    try:
        json.loads(text.strip())
        return 10
    except json.JSONDecodeError:
        return 0
```

Python 검사:

```python
def validate_python(text):
    try:
        ast.parse(text.strip())
        return 10
    except SyntaxError:
        return 0
```

Regex 검사:

```python
def validate_regex(text):
    try:
        re.compile(text.strip())
        return 10
    except re.error:
        return 0
```

주의:

`ast.parse`는 코드를 실행하지 않는다. 문법 구조만 확인한다.

## 8. format에 따라 채점기 선택

데이터셋에 `format`이 있으면 어떤 문법 검사를 할지 정할 수 있다.

```python
def grade_syntax(response, test_case):
    expected_format = test_case["format"]

    if expected_format == "json":
        return validate_json(response)
    if expected_format == "python":
        return validate_python(response)

    return validate_regex(response)
```

예:

```json
{
  "task": "Write a regex for AWS access key IDs",
  "format": "regex"
}
```

이 경우 `validate_regex`를 사용한다.

## 9. Model Score + Syntax Score

모델 점수와 문법 점수를 합쳐 최종 점수를 만든다.

```python
model_grade = grade_by_model(test_case, output)
model_score = model_grade["score"]
syntax_score = grade_syntax(output, test_case)

score = (model_score + syntax_score) / 2
```

의미:

- `model_score`: 과제를 잘 해결했는지
- `syntax_score`: 형식/문법이 맞는지
- `score`: 둘의 평균

예:

```text
JSON을 요청했는데 Python 코드가 나옴
→ model_score는 어느 정도 받을 수 있음
→ syntax_score는 0점
→ 최종 점수 하락
```

## 10. solution_criteria

완성형 평가에서는 테스트 케이스마다 평가 기준을 함께 저장한다.

```json
{
  "task": "Create AWS Lambda trust policy JSON",
  "format": "json",
  "solution_criteria": "Must include Version, Statement, Effect Allow, Action sts:AssumeRole, Principal Service lambda.amazonaws.com"
}
```

모델 채점 프롬프트에 넣는다.

```python
Criteria you should use to evaluate the solution:
<criteria>
{test_case["solution_criteria"]}
</criteria>
```

이렇게 하면 모델 채점기가 막연히 평가하지 않고, 구체적인 기준에 따라 평가한다.

## 11. 전체 평가 구조

최종 구조:

```text
generate_dataset()
→ task, format, solution_criteria 생성

run_prompt(test_case)
→ Claude가 답변 생성

grade_by_model(test_case, output)
→ 의미/정확성 평가

grade_syntax(output, test_case)
→ 문법/형식 평가

run_test_case(test_case)
→ output, score, reasoning 저장

run_eval(dataset)
→ 전체 평균 점수 계산
```

## 12. 시험 포인트

- Prompt evaluation은 프롬프트 성능을 객관적으로 측정하는 과정이다.
- Dataset은 여러 테스트 입력의 모음이다.
- `run_prompt`는 하나의 입력을 Claude에게 보내는 함수다.
- `run_test_case`는 하나의 테스트 결과를 만든다.
- `run_eval`은 전체 데이터셋을 평가한다.
- Model grader는 다른 AI 모델로 품질을 평가한다.
- Code grader는 코드로 문법/형식을 검사한다.
- Human grader는 사람이 직접 평가한다.
- `format` 필드는 어떤 syntax validator를 쓸지 결정한다.
- `solution_criteria`는 모델 채점의 기준을 더 구체적으로 만든다.
- 최종 점수는 보통 model score와 syntax score를 조합해서 만든다.
