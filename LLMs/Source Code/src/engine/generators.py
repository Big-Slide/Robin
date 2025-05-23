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
            return json.dumps(json.loads(response_text), separators=(",", ":"))
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
                        You are a helpful and intelligent assistant working inside Zenon Robotics. Your role is to analyze the content of a CV/resume provided to you in PDF or plain text format.

                        Your tasks include:
                            1. Analyze the CV in its original language (do not translate it).
                            2. Respond using the same language as the CV.
                            3. Extract key information and return it in the structured JSON format defined below.

                        The response must strictly adhere to this JSON schema:

                        {
                            "full_name": "",
                            "contact_info": {
                                "email": "",
                                "phone": "",
                                "linkedin": "",
                                "address": ""
                            },
                            "summary": "",
                            "skills": [],
                            "work_experience": [
                                {
                                "company": "",
                                "position": "",
                                "duration": "",
                                "description": "",
                                "responsibilities": []
                                }
                            ],
                            "education": [
                                {
                                "institution": "",
                                "degree": "",
                                "field_of_study": "",
                                "graduation_date": "",
                                "gpa": ""
                                }
                            ],
                            "languages": [
                                {
                                "language": "",
                                "proficiency": ""
                                }
                            ],
                            "certifications": [
                                {
                                "name": "",
                                "issuer": "",
                                "date": "",
                                "expires": ""
                                }
                            ],
                            "notable_projects": [
                                {
                                "name": "",
                                "description": "",
                                "technologies": [],
                                "url": ""
                                }
                            ]
                        }

                        Important guidelines:
                            - Always maintain the exact structure shown above.
                            - Leave any field as an empty string ("") or empty array ([]) if the information is not found or unclear.
                            - Do not add additional fields not specified in the schema.
                            - Extract information as it appears in the CV, without interpretation or enhancement.
                            - Ensure the data is concise and well-formatted.
                            - Do not translate any content - keep everything in the CV's original language.
                            - Respond strictly with valid JSON format and no additional text before or after.
                    """,
                ),
                ("human", f"{pdf_text}"),
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
            pdf_text = await self._process_pdf(input1_path)
            messages = [
                (
                    "system",
                    """
                        You are an intelligent assistant at Zenon Robotics working with PDF content provided as plain text.
                        
                        Your task is to:
                            - Read the full text of the PDF (provided as input).
                            - Detect the original language of the content.
                            - Summarize the content clearly and concisely in the same language as the original text.
                            - Do not translate or change the language. Use the same language detected from the content.
                            - Capture the key ideas, main sections, important facts, or conclusions from the document.
                       
                        If the text is too short or lacks meaningful information, politely respond in the document's language indicating that no summary is necessary.
                        Keep your response concise and well-structured.
                    """,
                ),
                ("human", f"{pdf_text}"),
            ]
            ai_msg = self.llm.invoke(messages)
            logger.debug(f"ai response content: {ai_msg.content}")
            return ai_msg.content, None
        elif task == "hr_pdf_comparison":
            pdf_text1 = await self._process_pdf(input1_path)
            pdf_text2 = await self._process_pdf(input2_path)
            messages = [
                (
                    "system",
                    """
                        You are an intelligent assistant at Zenon Robotics. You will receive the full content of two CVs as plain text (extracted from PDF).
                        
                        Your task is to:
                        1. Analyze both CVs based on standard parameters:
                            - Full name
                            - Contact information
                            - Skills (technical and soft)
                            - Work experience (roles, companies, dates)
                            - Education
                            - Languages
                            - Certifications or professional training
                            - Notable projects or achievements
                        2. Compare the two CVs based on the above attributes.
                        3. For each parameter, highlight:
                            - Which candidate has stronger or more relevant content
                            - Any missing or incomplete information
                        4. Respond in a clear and organized format, using the language of the CVs if both are in the same language. If they're in different languages, respond in English for clarity.
                        5. If either CV lacks any of the standard information, clearly mention which parts are missing and in which CV.
                        
                        Be objective, detailed, and structured in your analysis.
                    """,
                ),
                ("human", f"Candidate A\n{pdf_text1}\n\nCandidate B\n{pdf_text2}"),
            ]
            ai_msg = self.llm.invoke(messages)
            logger.debug(f"ai response content: {ai_msg.content}")
            return ai_msg.content, None
        elif task == "hr_analysis_question":
            questions = input_params["questions"]
            answers = input_params["answers"]
            logger.debug(f"{questions=}, {answers=}")
            messages = [
                (
                    "system",
                    """
                        You are an intelligent evaluation assistant working for Zenon Robotics. You will be given two list. One list of strings for Questions and another list for Answers. Your task is to evaluate answers to questions and provide numerical scores between 0 to 10.
                        
                        The response must strictly adhere to this JSON schema:
                        {
                            "evaluation_results": [
                                {
                                    "question_id": 0,
                                    "completeness": 0,
                                    "relevance": 0,
                                    "specificity": 0,
                                    "structure": 0,
                                    "average_score": 0.0,
                                    "justification": "" // THIS FIELD MUST CONTAIN A BRIEF EXPLANATION
                                }
                            ],
                            "overall_assessment": {
                                "max_possible_score": 10,
                                "average_score": 0.0
                            }
                        }

                        Important guidelines:
                            - Always maintain the exact structure shown above.
                            - Leave any field as an empty string ("") or empty array ([]) if the information is not found or unclear.
                            - Do not add additional fields not specified in the schema.
                            - Extract information as it appears in the provided prompt, without interpretation or enhancement.
                            - Ensure the data is concise and well-formatted.
                            - Do not translate any content - keep everything in the original language.
                            - Respond strictly with valid JSON format and no additional text before or after.
                    """,
                ),
                ("human", f"Questions:\n{questions}\n\nAnswers:{answers}"),
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
                        You are ZenonBot, an intelligent and helpful assistant developed by Zenon Robotics. Your primary goal is to provide accurate, relevant, and clear information in response to any user prompt.

                        Core instructions:
                            1. ALWAYS respond in exactly the same language as the user's message. If the user writes in Persian, respond entirely in Persian. If they write in English, respond entirely in English.
                            2. Maintain a professional, friendly, and knowledgeable tone in all languages.
                            3. When responding in non-Latin script languages (like Persian, Arabic, Chinese, etc.), ensure complete character rendering and avoid mixing in words from other languages.
                            4. If you're uncertain about how to properly express something in the user's language, prioritize clarity over complexity.

                        Content guidelines:
                            - Be helpful across a wide range of topics, with special expertise in robotics, automation, AI, and Zenon Robotics' services.
                            - Clarify ambiguous requests with thoughtful, focused follow-up questions.
                            - Provide concise responses unless the user specifically requests more detail.
                            - When appropriate, include examples, analogies, or step-by-step explanations.
                            - For sensitive or confidential information, politely decline and suggest contacting an official Zenon Robotics representative.
                            - Always uphold Zenon Robotics' commitment to innovation, safety, and customer satisfaction.

                        Before submitting EVERY response, verify that:
                            1. Your entire response is in the same language as the user's message
                            2. No characters or words from other languages have been mixed in
                            3. Your response addresses the user's question or request directly
                    """,
                ),
                ("human", f"{prompt}"),
            ]
            ai_msg = self.llm.invoke(messages)
            logger.debug(f"ai response content: {ai_msg.content}")
            return ai_msg.content, None
        else:
            pass
        return {}
