from google.generativeai import GenerationConfig, GenerativeModel
from google.generativeai.types import HarmCategory, HarmBlockThreshold, SafetySettingDict
from src.config.logging import logger
from typing import Optional, List


def _create_generation_config() -> GenerationConfig:
    """
    Creates and returns a generation configuration for the Gemini API.
    """
    try:
        gen_config = GenerationConfig(
            temperature=0.0,
            top_p=1.0,
            candidate_count=1,
            max_output_tokens=8192,
        )
        return gen_config
    except Exception as e:
        logger.error(f"Error creating generation configuration: {e}")
        raise


def _create_safety_settings() -> List[SafetySettingDict]:
    """
    Creates safety settings for content generation using the Gemini API.
    """
    try:
        safety_settings = [
            {"category": HarmCategory.HARM_CATEGORY_HATE_SPEECH, "threshold": HarmBlockThreshold.BLOCK_NONE},
            {"category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, "threshold": HarmBlockThreshold.BLOCK_NONE},
            {"category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, "threshold": HarmBlockThreshold.BLOCK_NONE},
            {"category": HarmCategory.HARM_CATEGORY_HARASSMENT, "threshold": HarmBlockThreshold.BLOCK_NONE},
            # {"category": HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY, "threshold": HarmBlockThreshold.BLOCK_NONE},
        ]
        return safety_settings
    except Exception as e:
        logger.error(f"Error creating safety settings: {e}")
        raise


def generate(model: GenerativeModel, contents: List[str]) -> Optional[str]:
    """
    Generates a response using the provided model and contents.

    Args:
        model (GenerativeModel): The generative model instance.
        contents (List[str]): The list of content parts (as strings).

    Returns:
        Optional[str]: The generated response text, or None if an error occurs.
    """
    try:
        logger.info("Generating response from Gemini")
        response = model.generate_content(
            contents,
            generation_config=_create_generation_config(),
            safety_settings=_create_safety_settings()
        )

        if not response.text:
            logger.error("Empty response from the model")
            return None

        logger.info("Successfully generated response")
        return response.text
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return None