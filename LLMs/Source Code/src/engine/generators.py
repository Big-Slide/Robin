from loguru import logger
import os
from config.config_handler import config
from langchain_ollama import ChatOllama
# from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import PyPDF2


class LLMGenerator:
    def __init__(self):
        self.llm = ChatOllama(
            base_url=config.CORE_BASE_URL,
            model=config.MODEL_ID,
            temperature=config.MODEL_TEMPERATURE,
            num_predict=config.MODEL_NUM_PREDICT,
            top_p=config.MODEL_TOP_P,
        )

    async def process_pdf(self, filepath: str) -> str:
        pdf_content = ""
        with open(filepath, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                pdf_content += page.extract_text() + "\n"
        return pdf_content

    async def process_task(self, task: str, input1_path: str, input2_path: str = None):
        if task == "hr_pdf_analysis":
            pdf_text = self.process_pdf(input1_path)
            messages = [
                (
                    "system",
                    "You are a helpful Persian assistant inside Robin company, and your job is to summarize or incase need translate too persian the CV provided to you and extract key attributes in persian language. Please answer questions in the asked language.",
                ),
                ("human", f":\n\n{pdf_text}"),
            ]
            # messages = [
            #     (
            #         "system",
            #         "You are a helpful assistant that translates English to French. Translate the user sentence.",
            #     ),
            #     ("human", "I love programming."),
            # ]
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
