from langchain_core.messages.utils import (
    trim_messages,
    count_tokens_approximately
)

def pre_model_hook(state):
    """ Gọi mỗi khi Agent được gọi trước khi gửi vào LLM.
    Dùng để cắt bớt lịch sử hội thoại nếu vượt quá giới hạn token"""
    trimmed_messages = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=2000,
        start_on="human",
        end_on=("human", "tool"),
    )
    return {"llm_input_messages": trimmed_messages}