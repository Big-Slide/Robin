from loguru import logger
from config.config_handler import config
from langchain_ollama import ChatOllama
from typing import Union, Dict
from core.cv_generator import CVGenerator
import zipfile
import tempfile
import os
import asyncio
from core.prompt import PromptHandler
from core import utils


class LLMGenerator:
    def __init__(self):
        self._current_state = {}
        self.prompt_handler = PromptHandler()
        self._set_model("chat")

    def _set_model(self, task: str, model: str = None):
        params = self.prompt_handler.get_model_params(task)
        if model is None:
            model = params["model"]
        num_predict = params["num_predict"]
        num_ctx = params["num_ctx"]
        if (
            model == self._current_state.get("model", None)
            and num_predict == self._current_state.get("num_predict", None)
            and num_ctx == self._current_state.get("num_ctx", None)
        ):
            return
        self.llm = ChatOllama(
            base_url=config.CORE_BASE_URL,
            model=model,
            temperature=config.MODEL_TEMPERATURE,
            num_predict=num_predict,
            top_p=config.MODEL_TOP_P,
            num_ctx=num_ctx,
        )
        self.cv_generator = CVGenerator(self.llm)
        self._current_state = {
            "model": model,
            "num_predict": num_predict,
            "num_ctx": num_ctx,
        }

    async def _process_zip_file(self, zip_path: str, files_type: str) -> Dict[str, str]:
        """
        Extract and process all files from a ZIP archive.

        Args:
            zip_path: Path to the ZIP file

        Returns:
            Dictionary mapping filenames to their extracted text content
        """
        contents = {}
        files = []

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            # Get list of files with type [files_type] from the ZIP
            for f in zip_ref.namelist():
                if (
                    not f.startswith("__MACOSX/")
                    and utils.get_file_type(f) == files_type
                ):
                    files.append(f)
            if not files:
                return contents

            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract only specified files
                for f in files:
                    zip_ref.extract(f, temp_dir)

                # Create each file processing task
                tasks = []
                for f in files:
                    temp_file_path = os.path.join(temp_dir, f)
                    if os.path.exists(temp_file_path):
                        tasks.append(self.__process_single_file(f, temp_file_path))

                # Process all files concurrently
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    for result in results:
                        if isinstance(result, tuple) and len(result) == 2:
                            filename, content = result
                            contents[filename] = content
                        elif isinstance(result, Exception):
                            logger.error(
                                f"Error processing file ({filename}): {result}"
                            )
        return contents

    async def __process_single_file(self, filename: str, filepath: str) -> tuple:
        try:
            filetype = utils.get_file_type(filename)
            if filetype == "pdf":
                content = await utils.get_pdf_content(filepath)
            elif filetype == "image":
                content = await utils.img_to_b64(filepath)
            else:
                logger.warning(f"The {filetype} filetype is not supported. {filename=}")
                content = ""
            return filename, content
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
            return filename, ""

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
        self._set_model(task=task, model=model)
        if task == "hr_pdf_analysis":
            pdf_text = await utils.get_pdf_content(input1_path)
            messages = self.prompt_handler.get_messages(task, pdf_text)
            ai_msg = self.llm.invoke(messages)
            logger.debug(f"ai response content: {ai_msg.content}")
            try:
                resp = utils.extract_json_from_response(ai_msg.content)
            except Exception as e:
                logger.opt(exception=False).warning(
                    "Failed to parse response to json", e=e.args
                )
                resp = ai_msg.content
            return resp, None
        elif task == "pdf_analysis":
            pdf_text = await utils.get_pdf_content(input1_path)
            messages = self.prompt_handler.get_messages(task, pdf_text)
            ai_msg = self.llm.invoke(messages)
            logger.debug(f"ai response content: {ai_msg.content}")
            return ai_msg.content, None
        elif task == "hr_pdf_comparison":
            pdf_text1 = await utils.get_pdf_content(input1_path)
            pdf_text2 = await utils.get_pdf_content(input2_path)
            messages = self.prompt_handler.get_messages(
                task, f"CV 1:\n{pdf_text1}\n\CV 2:\n{pdf_text2}"
            )
            ai_msg = self.llm.invoke(messages)
            logger.debug(f"ai response content: {ai_msg.content}")
            return ai_msg.content, None
        elif task == "hr_pdf_zip_comparison":
            results = await self._process_zip_file(input1_path, "pdf")

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

            results = await self._process_zip_file(input1_path, "pdf")
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
                resp = utils.extract_json_from_response(ai_msg.content)
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
        elif task == "chat_multimodal":
            # TODO: handle more file types
            # TODO: handle txt
            human_message = []
            file_type = utils.get_file_type(input1_path)
            file_content = self.__process_single_file(input1_path)
            if file_type == "image":
                human_message.append(
                    {
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{file_content}",
                    }
                )
            elif file_type == "pdf":
                # TODO: handle pdf
                raise ValueError("This filetype is not supported yet")
            human_message.append(
                {
                    "type": "text",
                    "text": input_params["prompt"],
                }
            )
            messages = self.prompt_handler.get_messages(task, human_message)
            ai_msg = self.llm.invoke(messages)
            logger.debug(f"ai response content: {ai_msg.content}")
            return ai_msg.content, None
        elif task == "painting_analysis":
            # TODO: handle single image
            lang = input_params["lang"]
            results = await self._process_zip_file(input1_path, "image")
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
        elif task == "ocr":
            filetype = utils.get_file_type(input1_path)
            human_message = []
            if filetype == "image":
                content = await utils.img_to_b64(input1_path)
                human_message.append(
                    {
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{content}",
                    }
                )
                human_message.append(
                    {
                        "type": "text",
                        "text": "Please extract all text from this image using OCR. The image may contain text in English, Persian, or Arabic. Return the results in the format that specified in your system instructions.",
                    }
                )
            else:
                raise ValueError("This filetype is not supported yet")
            messages = self.prompt_handler.get_messages(task, human_message)
            ai_msg = self.llm.invoke(messages)
            logger.debug(f"ai response content: {ai_msg.content}")
            return ai_msg.content, None
        elif task == "ocr_json":
            filetype = utils.get_file_type(input1_path)
            human_message = []
            if filetype == "image":
                content = await utils.img_to_b64(input1_path)
                human_message.append(
                    {
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{content}",
                    }
                )
                human_message.append(
                    {
                        "type": "text",
                        "text": "Please extract all text from this image using OCR. The image may contain text in English, Persian, or Arabic. Return the results in JSON format as specified in your system instructions.",
                    }
                )
            else:
                raise ValueError("This filetype is not supported yet")
            messages = self.prompt_handler.get_messages(task, human_message)
            ai_msg = self.llm.invoke(messages)
            logger.debug(f"ai response content: {ai_msg.content}")
            return ai_msg.content, None
        else:
            raise ValueError(f"Task {task} is not supported")
