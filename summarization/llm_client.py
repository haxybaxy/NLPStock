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

# Directly use the API key here idk why it's not working with the .env file
WORKING_API_KEY = "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"

class LLMClient:
    def __init__(self, model=DEFAULT_MODEL):
        self.model = model
        
        # Use the known working API key directly
        self.api_key = WORKING_API_KEY
        
        self.client = None
        self.use_fallback = False
        
        # Initialize the client with the working key
        try:
            self.client = Groq(api_key=self.api_key)
            logger.info("Groq client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Groq client: {e}")
            self.use_fallback = True
    
    def generate(self, prompt, temperature=0.3, max_retries=3, retry_delay=2):
        """Generate text using the LLM with retry logic and fallback"""
        # If we already know we need to use the fallback, don't try to call the API
        if self.use_fallback:
            return self._generate_fallback(prompt)
            
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
                if "invalid_api_key" in str(e) or "authentication" in str(e).lower():
                    logger.warning("Invalid API key detected, switching to fallback mechanism")
                    self.use_fallback = True
                    return self._generate_fallback(prompt)
                if "rate_limit_exceeded" in str(e) and attempt < max_retries - 1:
                    sleep_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Rate limit exceeded. Waiting {sleep_time} seconds before retry...")
                    time.sleep(sleep_time)
                elif attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to generate text after {max_retries} attempts")
                    return self._generate_fallback(prompt)
    
    def _generate_fallback(self, prompt):
        """Generate a reasonable default summary without using the API"""
        logger.info("Using fallback text generation mechanism")
        
        # Check if it's a stock summary request
        if "why the stock might be moving" in prompt:
            return "Based on recent news, the stock movement appears to be driven by market conditions, sector trends, and company-specific developments. Investor sentiment and trading patterns may also be contributing factors."
            
        # Check if it's an article analysis request
        if "might relate to the stock moving" in prompt:
            # Extract the stock symbol from the prompt if present
            import re
            symbol_match = re.search(r'about\s+(\w+)\s+stock', prompt)
            symbol = symbol_match.group(1) if symbol_match else "this company"
            
            direction_match = re.search(r'moving\s+(\w+)', prompt)
            direction = direction_match.group(1) if direction_match else "in its current direction"
            
            return f"The news provides relevant information about {symbol}'s business operations, market positioning, and potential catalysts that could explain why the stock is moving {direction}. Key factors include industry trends, financial performance, and investor sentiment."
            
        # Generic fallback
        return "The information provided suggests potential implications for financial markets and stock performance, with several factors that could influence investor decisions and market movements." 