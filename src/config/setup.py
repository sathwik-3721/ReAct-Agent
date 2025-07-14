from src.config.logging import logger
from typing import Dict, Any
import yaml


class Config:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Config, cls).__new__(cls)
            # The following line ensures that the __init__ method is only called once.
            cls._instance.__initialized = False
        return cls._instance
    
    def __init__(self, config_path: str = "./config/config.yml"):
        """
        Initialize the Config class.

        Args:
        - config_path (str): Path to the YAML configuration file.
        """
        if self.__initialized:
            return
        self.__initialized = True
        
        self.__config = self._load_config(config_path)
        self.GEMINI_API_KEY = self.__config['gemini_api_key']
        self.MODEL_NAME = self.__config['model_name']

    @staticmethod
    def _load_config(config_path: str) -> Dict[str, Any]:
        """
        Load the YAML configuration from the given path.

        Args:
        - config_path (str): Path to the YAML configuration file.

        Returns:
        - dict: Loaded configuration data.
        """
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            logger.error(f"Failed to load the configuration file. Error: {e}")
            raise


# Create a singleton instance of the Config class
config = Config()