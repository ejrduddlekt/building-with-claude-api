import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Text Chunking
# ---------------------------------------------------------------------------
#
# RAG(Retrieval Augmented Generation)는 질문과 관련 있는 문서 조각을 찾아서
# Claude prompt에 넣어주는 방식입니다.
#
# 전체 흐름:
#
# 긴 문서
#   ↓
# 작은 chunk들로 분할
#   ↓
# 사용자 질문과 관련 있는 chunk 검색
#   ↓
# 검색된 chunk를 Claude prompt에 추가
#   ↓
# Claude가 관련 문맥을 바탕으로 답변
#
# chunk를 너무 엉성하게 나누면 질문과 관계없는 정보가 검색될 수 있습니다.
# 따라서 chunking 방식은 RAG 답변 품질에 직접 영향을 줍니다.


# ---------------------------------------------------------------------------
# 1. Size-based chunking
# ---------------------------------------------------------------------------

def chunk_by_char(text, chunk_size=150, chunk_overlap=20):
    # 가장 단순한 방식입니다.
    # 문자열을 일정한 글자 수만큼 잘라 chunk list를 만듭니다.
    #
    # 파라미터:
    #
    # text:
    #   나눌 원본 문서 문자열입니다.
    #
    # chunk_size:
    #   chunk 하나에 최대 몇 글자를 넣을지 정합니다.
    #   기본값 150이면 한 chunk에 최대 150글자가 들어갑니다.
    #
    # chunk_overlap:
    #   이전 chunk의 마지막 부분을 다음 chunk에 몇 글자만큼 다시 포함할지 정합니다.
    #   기본값 20이면 이전 chunk의 마지막 20글자가 다음 chunk 앞에도 반복됩니다.
    #
    #   overlap이 필요한 이유:
    #   글자 수 기준으로 자르면 중요한 단어나 문장이 경계에서 잘릴 수 있습니다.
    #   일부 내용을 겹치게 넣으면 다음 chunk에서도 앞 문맥을 조금 볼 수 있습니다.
    #
    # 예:
    #
    # text = "ABCDEFGHIJKLMN"
    # chunk_size = 5
    # chunk_overlap = 2
    #
    # 결과:
    # ["ABCDE", "DEFGH", "GHIJK", "JKLMN"]
    #
    # overlap이 필요한 이유:
    # 글자 수 기준으로 자르면 문장이나 단어가 중간에서 끊길 수 있습니다.
    # 이전 chunk의 마지막 부분을 다음 chunk에도 조금 포함하면
    # 잘린 문맥을 어느 정도 보완할 수 있습니다.
    chunks = []
    start_idx = 0

    while start_idx < len(text):
        # 마지막 chunk는 chunk_size보다 짧을 수 있습니다.
        # min()을 사용해서 문자열 길이를 넘어가지 않게 합니다.
        end_idx = min(start_idx + chunk_size, len(text))

        chunk_text = text[start_idx:end_idx]
        chunks.append(chunk_text)

        # 아직 문서 끝이 아니라면 overlap만큼 뒤로 돌아갑니다.
        #
        # 예:
        # 현재 chunk가 0~149 글자라면 다음 chunk는 130부터 시작합니다.
        # 130~149 부분이 두 chunk에 함께 포함됩니다.
        start_idx = (
            end_idx - chunk_overlap if end_idx < len(text) else len(text)
        )

    return chunks


# ---------------------------------------------------------------------------
# 2. Sentence-based chunking
# ---------------------------------------------------------------------------

def chunk_by_sentence(text, max_sentences_per_chunk=5, overlap_sentences=1):
    # 글자 수가 아니라 문장 단위로 나눕니다.
    #
    # 파라미터:
    #
    # text:
    #   나눌 원본 문서 문자열입니다.
    #
    # max_sentences_per_chunk:
    #   chunk 하나에 최대 몇 개의 문장을 넣을지 정합니다.
    #   기본값 5이면 한 chunk에 최대 5문장이 들어갑니다.
    #
    # overlap_sentences:
    #   이전 chunk의 마지막 문장을 다음 chunk에 몇 개만큼 다시 포함할지 정합니다.
    #   기본값 1이면 이전 chunk의 마지막 1문장이 다음 chunk의 첫 문장으로 반복됩니다.
    #
    # 예:
    #
    # 문장이 8개 있고:
    # max_sentences_per_chunk = 5
    # overlap_sentences = 1
    #
    # 첫 chunk: 1, 2, 3, 4, 5번 문장
    # 다음 chunk:             5, 6, 7, 8번 문장
    #
    # 정규식 의미:
    # (?<=[.!?]) : 바로 앞에 마침표, 느낌표, 물음표가 있는 위치
    # \s+         : 그 뒤에 이어지는 하나 이상의 공백
    #
    # 즉, 문장이 끝난 뒤의 공백을 기준으로 split합니다.
    sentences = re.split(r"(?<=[.!?])\s+", text)

    chunks = []
    start_idx = 0

    while start_idx < len(sentences):
        end_idx = min(start_idx + max_sentences_per_chunk, len(sentences))

        current_chunk = sentences[start_idx:end_idx]
        chunks.append(" ".join(current_chunk))

        # 문장 overlap을 남기고 다음 chunk로 이동합니다.
        #
        # 예:
        # max_sentences_per_chunk = 5
        # overlap_sentences = 1
        #
        # 첫 chunk: 0~4번 문장
        # 다음 chunk: 4~8번 문장
        start_idx += max_sentences_per_chunk - overlap_sentences

    return chunks


# ---------------------------------------------------------------------------
# 3. Structure-based chunking
# ---------------------------------------------------------------------------

def chunk_by_section(document_text):
    # Markdown 문서의 ## 헤더를 기준으로 나눕니다.
    #
    # 파라미터:
    #
    # document_text:
    #   Markdown 문서 전체를 읽은 문자열입니다.
    #
    # 이 함수는 chunk_size나 overlap 값을 받지 않습니다.
    # 글자 수가 아니라 문서 안에 이미 존재하는 ## 제목을 경계로 사용하기 때문입니다.
    #
    # report.md에는 이런 구조가 있습니다.
    #
    # ## Section 1: Medical Research
    # ...
    #
    # ## Section 2: Software Engineering
    # ...
    #
    # 문서 구조가 일정하다면 섹션 단위 chunk가 가장 읽기 좋고 의미도 잘 보존됩니다.
    #
    # 단점:
    # PDF, 일반 텍스트처럼 일정한 헤더 구조가 없는 문서에는 바로 적용하기 어렵습니다.
    pattern = r"\n## "
    return re.split(pattern, document_text)


# ---------------------------------------------------------------------------
# 4. Semantic-based chunking
# ---------------------------------------------------------------------------
#
# Semantic chunking은 문장의 "의미"가 비슷한지 비교해서 chunk를 나누는 방식입니다.
#
# 예:
#
# 의료 연구 문장들
#   ↓ 의미가 유사함
# 하나의 chunk
#
# 소프트웨어 버그 문장들
#   ↓ 의미가 유사함
# 다른 chunk
#
# 이 방식은 embedding이나 NLP 모델이 필요하고 계산 비용도 더 큽니다.
# 이번 첫 강의에서는 개념만 확인하고 직접 구현하지 않습니다.


# ---------------------------------------------------------------------------
# 5. 출력 helper
# ---------------------------------------------------------------------------

def print_chunks(title, chunks):
    print("=" * 80)
    print(title)
    print(f"Chunk count: {len(chunks)}")
    print("=" * 80)

    for index, chunk in enumerate(chunks, start=1):
        print()
        print(f"[Chunk {index}]")
        print(chunk)
        print()
        print("-" * 80)


def run():
    # 같은 report.md 문서를 세 가지 방식으로 나눠서 비교합니다.
    #
    # 직접 실행:
    # python main.py
    #
    # 비교할 점:
    # 1. 글자 수 기준 chunk는 문장이 중간에서 끊기는가?
    # 2. 문장 기준 chunk는 문맥이 더 자연스러운가?
    # 3. 섹션 기준 chunk는 제목과 내용이 함께 유지되는가?
    report_path = Path(__file__).with_name("report.md")

    with report_path.open("r", encoding="utf-8") as file:
        text = file.read()

    char_chunks = chunk_by_char(
        text,
        # 출력이 너무 길어지지 않도록 예제에서는 chunk 하나를 최대 500글자로 만듭니다.
        chunk_size=500,
        # 각 chunk 사이에 50글자를 겹치게 넣어서 경계의 문맥을 일부 보존합니다.
        chunk_overlap=50,
    )

    sentence_chunks = chunk_by_sentence(
        text,
        # chunk 하나에 최대 5문장을 넣습니다.
        max_sentences_per_chunk=5,
        # 이전 chunk의 마지막 1문장을 다음 chunk에도 다시 넣습니다.
        overlap_sentences=1,
    )

    section_chunks = chunk_by_section(text)

    print_chunks("1. Size-based chunking", char_chunks)
    print()
    print_chunks("2. Sentence-based chunking", sentence_chunks)
    print()
    print_chunks("3. Structure-based chunking", section_chunks)
