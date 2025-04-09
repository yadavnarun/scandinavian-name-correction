from django.apps import AppConfig
import logging
import time
from .matcher import SmartNameMatcher

logger = logging.getLogger(__name__)

smart_matcher_instance = None

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        """
        This method is called once when Django starts.
        Initialize heavy resources here.
        """
        global smart_matcher_instance
        
        if not smart_matcher_instance:
            logger.info("Django AppConfig ready: Initializing SmartNameMatcher instance...")
            start_time = time.time()
            try:
                cache_file = "name_metaphone_cache.v1.pkl.gz"
                smart_matcher_instance = SmartNameMatcher(use_cache=True, cache_file=cache_file)
                logger.info(f"SmartNameMatcher initialized successfully in {time.time() - start_time:.2f}s via AppConfig.")
            except Exception as e:
                logger.exception(f"CRITICAL ERROR: Failed to initialize SmartNameMatcher in AppConfig: {e}")
        else:
             logger.info("SmartNameMatcher instance already initialized.")


def get_matcher_instance():
    if smart_matcher_instance is None:
        logger.error("SmartNameMatcher instance requested before initialization or initialization failed!")
        raise RuntimeError("SmartNameMatcher is not available.")
    return smart_matcher_instance