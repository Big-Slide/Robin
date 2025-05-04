from loguru import logger
import os
from config.config_handler import config
from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, HumanMessage


class LLMGenerator:
    def __init__(self):
        self.llm = ChatOllama(
            base_url=config.CORE_BASE_URL,
            model=config.MODEL_ID,
            temperature=config.MODEL_TEMPERATURE,
            # num_predict=1024,
        )

    async def process_pdf(filepath: str) -> str:
        pass

    async def process_task(self, task: str, input1_path: str, input2_path: str = None):
        if task == "hr_pdf_analysis":
            messages = [
                (
                    "system",
                    "You are a helpful assistant that translates English to French. Translate the user sentence.",
                ),
                ("human", "I love programming."),
            ]
            ai_msg = self.llm.ainvoke(messages)
            return {"text": ai_msg.content}
        elif task == "pdf_analysis":
            pass
        elif task == "hr_pdf_comparison":
            pass
        elif task == "hr_analysis_question":
            pass
        else:
            pass
        return {}
