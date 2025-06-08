from loguru import logger
from config.config_handler import config
from langchain_ollama import ChatOllama
from typing import Union, Dict
import PyPDF2
from core.cv_generator import CVGenerator
import json
import re
import zipfile
import tempfile
import os
import asyncio
from core.prompt import PromptHandler
import base64


class LLMGenerator:
    def __init__(self):
        self._current_model = None
        self._set_model()
        self.prompt_handler = PromptHandler()

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
            num_ctx=config.MODEL_NUM_CTX,
        )
        self.cv_generator = CVGenerator(self.llm)
        self._current_model = id_model

    async def _process_zip_pdfs(self, zip_path: str) -> Dict[str, str]:
        """
        Extract and process all PDF files from a ZIP archive.

        Args:
            zip_path: Path to the ZIP file

        Returns:
            Dictionary mapping PDF filenames to their extracted text content
        """
        pdf_contents = {}

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            # Get list of PDF files in the ZIP
            pdf_files = [
                f
                for f in zip_ref.namelist()
                if f.lower().endswith(".pdf") and not f.startswith("__MACOSX/")
            ]

            if not pdf_files:
                return pdf_contents

            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract only PDF files
                for pdf_file in pdf_files:
                    zip_ref.extract(pdf_file, temp_dir)

                # Process each PDF file
                tasks = []
                for pdf_file in pdf_files:
                    temp_pdf_path = os.path.join(temp_dir, pdf_file)
                    if os.path.exists(temp_pdf_path):
                        tasks.append(self.__process_single_pdf(pdf_file, temp_pdf_path))

                # Process all PDFs concurrently
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    for result in results:
                        if isinstance(result, tuple) and len(result) == 2:
                            filename, content = result
                            pdf_contents[filename] = content
                        elif isinstance(result, Exception):
                            logger.error(f"Error processing PDF: {result}")

        return pdf_contents

    async def _process_zip_images(self, zip_path: str) -> Dict[str, str]:
        """
        Extract and process all PDF files from a ZIP archive.

        Args:
            zip_path: Path to the ZIP file

        Returns:
            Dictionary mapping Image filenames to their base64 encoded text content
        """
        images_encoded = {}

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            # Get list of Image files in the ZIP
            image_files = [
                f
                for f in zip_ref.namelist()
                if (
                    f.lower().endswith(".jpg")
                    or f.lower().endswith(".jpeg")
                    or f.lower().endswith(".png")
                )
                and not f.startswith("__MACOSX/")
            ]

            if not image_files:
                return images_encoded

            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract only PDF files
                for image_file in image_files:
                    zip_ref.extract(image_file, temp_dir)

                # Process each Image file
                tasks = []
                for image_file in image_files:
                    temp_image_path = os.path.join(temp_dir, image_file)
                    if os.path.exists(temp_image_path):
                        tasks.append(
                            self.__process_single_image(image_file, temp_image_path)
                        )

                # Process all Images concurrently
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    for result in results:
                        if isinstance(result, tuple) and len(result) == 2:
                            filename, content = result
                            images_encoded[filename] = content
                        elif isinstance(result, Exception):
                            logger.error(f"Error processing Image: {result}")

        return images_encoded

    async def __process_single_pdf(self, filename: str, filepath: str) -> tuple:
        """
        Process a single PDF file and return filename with content.

        Args:
            filename: Original filename in the ZIP
            filepath: Temporary file path

        Returns:
            Tuple of (filename, content)
        """
        try:
            content = await self._process_pdf(filepath)
            return filename, content
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
            return filename, ""

    async def __process_single_image(self, filename: str, filepath: str) -> tuple:
        """
        Process a single PDF file and return filename with content.

        Args:
            filename: Original filename in the ZIP
            filepath: Temporary file path

        Returns:
            Tuple of (filename, content)
        """
        try:
            content = await self._process_image(filepath)
            return filename, content
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
            return filename, ""

    async def _process_pdf(self, filepath: str) -> str:
        pdf_content = ""
        with open(filepath, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                pdf_content += page.extract_text() + "\n"
        return pdf_content

    async def _process_image(self, filepath: str) -> str:
        with open(filepath, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

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
        logger.debug(
            f"{task=}, {input_params=}, {input1_path=}, {input2_path=}, {output_path=}, {model=}"
        )
        self._set_model(model=model)
        if task == "hr_pdf_analysis":
            pdf_text = await self._process_pdf(input1_path)
            messages = self.prompt_handler.get_messages(task, pdf_text)
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
            messages = self.prompt_handler.get_messages(task, pdf_text)
            ai_msg = self.llm.invoke(messages)
            logger.debug(f"ai response content: {ai_msg.content}")
            return ai_msg.content, None
        elif task == "hr_pdf_comparison":
            pdf_text1 = await self._process_pdf(input1_path)
            pdf_text2 = await self._process_pdf(input2_path)
            messages = self.prompt_handler.get_messages(
                task, f"CV 1:\n{pdf_text1}\n\CV 2:\n{pdf_text2}"
            )
            ai_msg = self.llm.invoke(messages)
            logger.debug(f"ai response content: {ai_msg.content}")
            return ai_msg.content, None
        elif task == "hr_pdf_zip_comparison":
            results = await self._process_zip_pdfs(input1_path)

            human_message = ""
            c = 1
            for filename, content in results.items():
                human_message += f'"CV {c}":\n{content}\n\n'
                c += 1
            logger.debug(f"{human_message=}")

            messages = self.prompt_handler.get_messages(task, human_message)
            ai_msg = self.llm.invoke(messages)
            logger.debug(f"ai response content: {ai_msg.content}")
            return ai_msg.content, None
        elif task == "hr_pdf_zip_compare_and_match":
            job_description = input_params["job_description"]

            results = await self._process_zip_pdfs(input1_path)
            human_message = ""
            c = 1
            for filename, content in results.items():
                human_message += (
                    f'"Job Description": {job_description}\n\n"CV {c}":\n{content}\n\n'
                )
                c += 1
            logger.debug(f"{human_message=}")

            messages = self.prompt_handler.get_messages(task, human_message)
            ai_msg = self.llm.invoke(messages)
            logger.debug(f"ai response content: {ai_msg.content}")
            return ai_msg.content, None
        elif task == "hr_analysis_question":
            questions = input_params["questions"]
            answers = input_params["answers"]
            messages = self.prompt_handler.get_messages(
                task, f"Questions:\n{questions}\n\nAnswers:{answers}"
            )
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
            messages = self.prompt_handler.get_messages(task, prompt)
            ai_msg = self.llm.invoke(messages)
            logger.debug(f"ai response content: {ai_msg.content}")
            return ai_msg.content, None
        elif task == "painting_analysis":
            if model is None:
                self._set_model(config.MODEL_MULTIMODAL_ID)
            lang = input_params["lang"]
            results = await self._process_zip_images(input1_path)
            human_message = []
            for filename, content in results.items():
                human_message.append(
                    {
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{content}",
                    }
                )
            if lang == "en":
                human_message.append(
                    {
                        "type": "text",
                        "text": "Please provide a comprehensive psychological analysis of this child's artwork. Please respond in English only",
                    }
                )
            elif lang == "fa":
                human_message.append(
                    {
                        "type": "text",
                        "text": "Please provide a comprehensive psychological analysis of this child's artwork. Please respond in Persian only",
                    }
                )
            elif lang == "ar":
                human_message.append(
                    {
                        "type": "text",
                        "text": "Please provide a comprehensive psychological analysis of this child's artwork. Please respond in Arabic only",
                    }
                )
            else:
                raise ValueError(f"lang {lang} is not supported")
            logger.debug(f"{human_message=}")
            messages = self.prompt_handler.get_messages(task, human_message)
            ai_msg = self.llm.invoke(messages)
            logger.debug(f"ai response content: {ai_msg.content}")
            return ai_msg.content, None
        else:
            raise ValueError(f"task {task} is not supported")
