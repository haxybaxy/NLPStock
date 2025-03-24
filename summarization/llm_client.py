import os
import logging
import time
from dotenv import load_dotenv
from groq import Groq

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Default model
DEFAULT_MODEL = "llama3-8b-8192"

class LLMClient:
    def __init__(self, model=DEFAULT_MODEL):
        self.model = model
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        self.client = Groq(api_key=self.api_key)
    
    def generate(self, prompt, temperature=0.3, max_retries=3, retry_delay=2):
        """Generate text using the LLM with retry logic"""
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.model,
                    temperature=temperature,
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"Error in LLM request (attempt {attempt+1}/{max_retries}): {e}")
                if "rate_limit_exceeded" in str(e) and attempt < max_retries - 1:
                    sleep_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Rate limit exceeded. Waiting {sleep_time} seconds before retry...")
                    time.sleep(sleep_time)
                elif attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to generate text after {max_retries} attempts")
                    return "" 