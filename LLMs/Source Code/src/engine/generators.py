from loguru import logger
from config.config_handler import config
from langchain_ollama import ChatOllama
from typing import Union, Dict
import PyPDF2
from core.cv_generator import CVGenerator
import json
import re


class LLMGenerator:
    def __init__(self):
        self._current_model = None
        self._set_model()

    def _set_model(self, model: str = None):
        if model is not None and model == self._current_model:
            return
        if model:
            id_model = model
        else:
            id_model = config.MODEL_ID
        self.llm = ChatOllama(
            base_url=config.CORE_BASE_URL,
            model=id_model,
            temperature=config.MODEL_TEMPERATURE,
            num_predict=config.MODEL_NUM_PREDICT,
            top_p=config.MODEL_TOP_P,
        )
        self.cv_generator = CVGenerator(self.llm)
        self._current_model = id_model

    async def _process_pdf(self, filepath: str) -> str:
        pdf_content = ""
        with open(filepath, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                pdf_content += page.extract_text() + "\n"
        return pdf_content

    def _extract_json_from_response(self, response_text):
        """
        Extracts a JSON object from a text response.
        Assumes the JSON is enclosed in curly braces {} or a code block.
        """
        try:
            # Try to directly parse if the whole response is JSON
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback: Extract the first JSON-like block from the text
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                json_str = json_match.group()
                try:
                    return json.dumps(json.loads(json_str), separators=(",", ":"))
                except json.JSONDecodeError as e:
                    raise ValueError("Found JSON block but could not parse it.") from e
            raise ValueError("No JSON object found in the response.")

    async def process_task(
        self,
        task: str,
        input1_path: str = None,
        input2_path: str = None,
        input_params: Dict = None,
        output_path: str = None,
        model: str = None,
    ) -> Union[str, str]:
        self._set_model(model=model)
        if task == "hr_pdf_analysis":
            pdf_text = await self._process_pdf(input1_path)
            messages = [
                (
                    "system",
                    """
                        You are a helpful and intelligent assistant working inside Robin Company. Your role is to analyze the content of a CV/resume provided to you in PDF or plain text format.
                        Your tasks include:
                        Analyze the CV in its original language (do not translate it).
                        Respond using the same language as the CV.
                        Extract key information and return it in the following structured JSON format:

                            {
                                "full_name": "",
                                "contact_info": "",
                                "skills": [],
                                "work_experience": [],
                                "education": [],
                                "languages": [],
                                "certifications": [],
                                "notable_projects": []
                            }

                        Leave any field blank or as an empty array ([]) if the information is not found or unclear.
                        Ensure the data is concise and well-formatted.
                        Do not translate or summarize — just extract and present the data accurately.
                        Always respond strictly in JSON format, using the CV’s original language for all values.
                    """,
                ),
                ("human", f":\n\n{pdf_text}"),
            ]
            ai_msg = self.llm.invoke(messages)
            logger.debug(f"ai response content: {ai_msg.content}")
            try:
                resp = self._extract_json_from_response(ai_msg.content)
            except Exception as e:
                logger.opt(exception=False).warning(
                    "Failed to parse response to json", e=e.args
                )
                resp = ai_msg.content
            return resp, None
        elif task == "pdf_analysis":
            pass
        elif task == "hr_pdf_comparison":
            pass
        elif task == "hr_analysis_question":
            pass
        elif task == "cv_generate":
            user_data = {}
            for question, response in input_params.items():
                if type(response) is str:
                    response = response.strip()
                user_data[question] = response
            cv_content = self.cv_generator.generate_cv_content(user_data)
            self.cv_generator.create_pdf_cv(cv_content, output_path)
            return None, output_path
        elif task == "chat":
            prompt = input_params["prompt"]
            messages = [
                (
                    "system",
                    """
                        You are ZenonBot, an intelligent and helpful assistant developed by Zenon Robotics. Your role is to provide accurate, relevant, and clear information in response to any user prompt.
                        You should always:
                            - Respond in the same language used in the user's prompt.
                            - Maintain a professional, friendly, and knowledgeable tone.
                            - Be helpful across a wide range of topics, especially robotics, automation, AI, and company-specific services.
                            - Clarify ambiguous requests with thoughtful follow-up questions.
                            - Respond concisely, unless more detail is clearly requested.
                            - Uphold Zenon Robotics' commitment to innovation, safety, and customer satisfaction.
                        If a question involves sensitive or confidential information, politely decline and suggest contacting an official Zenon Robotics representative.
                        When appropriate, include examples, analogies, or step-by-step explanations to improve clarity. Always aim to solve the user's problem or guide them to the best next step.
                    """,
                ),
                ("human", f":\n\n{prompt}"),
            ]
            ai_msg = self.llm.invoke(messages)
            logger.debug(f"ai response content: {ai_msg.content}")
            return ai_msg.content, None
        else:
            pass
        return {}
