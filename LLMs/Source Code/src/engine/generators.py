from loguru import logger
import os
from config.config_handler import config
from langchain_ollama import ChatOllama
from typing import Union, Dict

# from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import PyPDF2
from core.cv_generator import CVGenerator


class LLMGenerator:
    def __init__(self):
        self.llm = ChatOllama(
            base_url=config.CORE_BASE_URL,
            model=config.MODEL_ID,
            temperature=config.MODEL_TEMPERATURE,
            num_predict=config.MODEL_NUM_PREDICT,
            top_p=config.MODEL_TOP_P,
        )
        self.cv_generator = CVGenerator(self.llm)

    async def process_pdf(self, filepath: str) -> str:
        pdf_content = ""
        with open(filepath, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                pdf_content += page.extract_text() + "\n"
        return pdf_content

    async def process_task(
        self,
        task: str,
        input1_path: str = None,
        input2_path: str = None,
        input_params: Dict = None,
        output_path: str = None,
    ) -> Union[str, str]:
        if task == "hr_pdf_analysis":
            pdf_text = await self.process_pdf(input1_path)
            messages = [
                (
                    "system",
                    "You are a helpful Persian assistant inside Robin company, and your job is to summarize or incase need translate too persian the CV provided to you and extract key attributes in persian language. Please answer questions in the asked language.",
                ),
                ("human", f":\n\n{pdf_text}"),
            ]
            ai_msg = self.llm.invoke(messages)
            logger.debug(f"ai response content: {ai_msg.content}")
            return ai_msg.content, None
        elif task == "pdf_analysis":
            pass
        elif task == "hr_pdf_comparison":
            pass
        elif task == "hr_analysis_question":
            pass
        elif task == "cv_generate":
            user_data = {}
            for question, response in input_params.items():
                user_data[question] = response.strip()
            cv_content = self.cv_generator.generate_cv_content(user_data)
            self.cv_generator.create_pdf_cv(cv_content, output_path)
            return None, output_path
        else:
            pass
        return {}
