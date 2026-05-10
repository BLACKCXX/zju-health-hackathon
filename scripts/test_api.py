from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.llm_client import NO_API_KEY_MESSAGE, call_llm  # noqa: E402


def main() -> None:
    messages = [
        {"role": "system", "content": "你是一个严谨的医学学习助手。"},
        {"role": "user", "content": "请用一句话解释什么是病理生理学。"},
    ]
    result = call_llm(messages, role="answer", temperature=0.2)
    if result == NO_API_KEY_MESSAGE:
        print(NO_API_KEY_MESSAGE)
        return
    print(result)


if __name__ == "__main__":
    main()
