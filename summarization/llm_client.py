import os
import logging
import time
import re
from dotenv import load_dotenv
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import torch

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Default model - using bart-large-cnn for better summarization
DEFAULT_MODEL = "facebook/bart-large-cnn"

# Templates for stock-specific summaries
STOCK_UP_TEMPLATE = """
- {point1}
- {point2}
- {point3}
"""

STOCK_DOWN_TEMPLATE = """
- {point1}
- {point2}
- {point3}
"""

class LLMClient:
    def __init__(self, model=DEFAULT_MODEL):
        self.model = model
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.use_fallback = False
        self.pipeline = None
        self.tokenizer = None
        
        # Initialize the transformers model
        try:
            logger.info(f"Loading transformers model {model} on {self.device}")
            self.tokenizer = AutoTokenizer.from_pretrained(model)
            logger.info(f"Device set to use {self.device}")
            
            if self.device == "cuda":
                self.pipeline = pipeline(
                    "summarization", 
                    model=model, 
                    tokenizer=self.tokenizer,
                    device=0
                )
            else:
                # Load with standard settings for CPU
                self.pipeline = pipeline(
                    "summarization", 
                    model=model, 
                    tokenizer=self.tokenizer,
                    device=-1
                )
            logger.info("Transformers model loaded successfully")
        except Exception as e:
            logger.error(f"Error initializing transformers model: {e}")
            self.use_fallback = True
    
    def generate(self, prompt, temperature=0.3, max_retries=3, retry_delay=2):
        """Generate text using transformers with retry logic and fallback"""
        # Check for stock-specific queries to provide specialized outputs
        stock_info = self._extract_stock_info(prompt)
        
        # If we already know we need to use the fallback, don't try to call the pipeline
        if self.use_fallback:
            return self._generate_fallback(prompt, stock_info)
            
        for attempt in range(max_retries):
            try:
                # Clean and format the prompt for the model
                cleaned_prompt = self._clean_prompt(prompt)
                
                # Set the max input length based on model constraints
                max_length = 1024  # BART default
                input_tokens = self.tokenizer.encode(cleaned_prompt)
                
                # Truncate if needed
                if len(input_tokens) > max_length:
                    logger.warning(f"Input too long ({len(input_tokens)} tokens), truncating to {max_length}")
                    input_tokens = input_tokens[:max_length]
                    cleaned_prompt = self.tokenizer.decode(input_tokens)
                
                # Calculate appropriate max output length based on input length
                input_length = len(input_tokens)
                # For summarization: aim for roughly 1/3 of input length, with min and max bounds
                output_max_length = min(150, max(30, input_length // 3))
                output_min_length = max(15, min(output_max_length // 2, 30))
                
                # Generate summary - suppress the warning about max_length
                with open(os.devnull, 'w') as f:
                    import sys
                    old_stderr = sys.stderr
                    sys.stderr = f
                    
                    summary = self.pipeline(
                        cleaned_prompt,
                        max_length=output_max_length,
                        min_length=output_min_length,
                        do_sample=True if temperature > 0 else False,
                        temperature=max(temperature, 1e-6),  # Avoid 0 temperature
                        num_return_sequences=1
                    )
                    
                    sys.stderr = old_stderr
                
                # Process the summary to make it more concise
                result = summary[0]['summary_text'].strip()
                
                # Remove model prompt leakage and promotional content
                result = self._remove_prompt_leakage(result, cleaned_prompt)
                result = self._remove_promotional_content(result)
                
                # Remove redundant sentences that might appear in BART's output
                result = self._clean_redundant_sentences(result)
                
                # For stock queries, enhance with stock-specific formatting
                if stock_info["is_stock_query"]:
                    result = self._enhance_stock_summary(result, stock_info)
                
                return result
            
            except Exception as e:
                logger.error(f"Error in transformers request (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to generate text after {max_retries} attempts")
                    return self._generate_fallback(prompt, stock_info)
    
    def _remove_promotional_content(self, text):
        """Remove promotional content from the generated text"""
        # Filter out promotional sentences
        promotional_patterns = [
            r".*[Uu]nlock stock picks.*",
            r".*broker[- ]level newsfeed.*",
            r".*powers Wall Street.*",
            r".*[Ss]ubscribe.*for more.*",
            r".*premium content.*",
            r".*unlock.*analysis.*",
            r".*exclusive.*insights.*",
            r".*register.*account.*",
            r".*sign up.*newsletter.*"
        ]
        
        sentences = re.split(r'(?<=[.!?])\s+', text)
        filtered_sentences = []
        
        for sentence in sentences:
            is_promotional = False
            for pattern in promotional_patterns:
                if re.match(pattern, sentence, re.DOTALL):
                    is_promotional = True
                    break
            if not is_promotional:
                filtered_sentences.append(sentence)
        
        return ' '.join(filtered_sentences)
    
    def _remove_prompt_leakage(self, result, prompt):
        """Remove any parts of the prompt that leaked into the result"""
        # Check for common prompt patterns
        patterns = [
            r"Identify the key factors affecting.*?:",
            r"Identify key factors.*?:",
            r"Summarize the key.*?:",
            r"Summarize key.*?:",
            r"Company:.*?Content:",
            r"Stock direction:.*?Content:",
            r"Content:",
            r"Based on the following information:",
            r"The following information indicates that",
            r"Based on.*?information:.*?",
            r"List the three most important factors.*?:"
        ]
        
        cleaned_result = result
        for pattern in patterns:
            cleaned_result = re.sub(pattern, "", cleaned_result, flags=re.IGNORECASE | re.DOTALL)
        
        # Clean up any repeated colons or excess whitespace
        cleaned_result = re.sub(r"\s*:\s*:", ":", cleaned_result)
        cleaned_result = re.sub(r"\s+", " ", cleaned_result).strip()
        
        return cleaned_result
    
    def _extract_stock_info(self, prompt):
        """Extract stock-related information from the prompt"""
        stock_info = {
            "is_stock_query": False,
            "symbol": "",
            "direction": "",
            "content": ""
        }
        
        # Check if it's a stock-related query
        if "stock" in prompt.lower() and ("moving" in prompt.lower() or "price" in prompt.lower()):
            stock_info["is_stock_query"] = True
            
            # Extract symbol if present - check multiple patterns
            symbol_match = re.search(r'about\s+(\w+)\s+stock', prompt)
            if symbol_match:
                stock_info["symbol"] = symbol_match.group(1)
            else:
                # Check for "summaries about SYMBOL"
                summaries_match = re.search(r'news summaries about (\w+)[,\s]', prompt)
                if summaries_match:
                    stock_info["symbol"] = summaries_match.group(1)
                else:
                    # Check for typical stock symbols in caps (3-5 letters)
                    symbol_match = re.search(r'\b([A-Z]{3,5})\b', prompt)
                    if symbol_match:
                        stock_info["symbol"] = symbol_match.group(1)
            
            # Extract direction if present
            if "up" in prompt.lower() or "increase" in prompt.lower() or "rising" in prompt.lower() or "positive" in prompt.lower():
                stock_info["direction"] = "up"
            elif "down" in prompt.lower() or "decrease" in prompt.lower() or "falling" in prompt.lower() or "decline" in prompt.lower() or "miss" in prompt.lower() or "negative" in prompt.lower():
                stock_info["direction"] = "down"
            else:
                direction_match = re.search(r'moving\s+(\w+)', prompt)
                if direction_match:
                    direction = direction_match.group(1).lower()
                    if direction in ["up", "down"]:
                        stock_info["direction"] = direction
            
            # Extract content
            processed_info_match = re.search(r'Processed information: (.*?)$', prompt, re.DOTALL)
            summaries_match = re.search(r'Based on these news summaries.*?:\s+(.*?)$', prompt, re.DOTALL)
            
            if processed_info_match:
                stock_info["content"] = processed_info_match.group(1)
            elif summaries_match:
                stock_info["content"] = summaries_match.group(1)
            
            # If content has direct negative indicators, update direction
            if stock_info["content"] and stock_info["direction"] == "":
                if any(term in stock_info["content"].lower() for term in ["miss", "decline", "drop", "fall", "decrease", "down", "lower", "negative", "below expectations"]):
                    stock_info["direction"] = "down"
                elif any(term in stock_info["content"].lower() for term in ["beat", "exceed", "rise", "increase", "up", "higher", "positive", "above expectations"]):
                    stock_info["direction"] = "up"
        
        return stock_info
    
    def _enhance_stock_summary(self, summary, stock_info):
        """Enhance the stock summary with more structure and context"""
        if not stock_info["is_stock_query"] or not summary:
            return summary
        
        # Extract key points from the summary
        sentences = [s.strip() for s in re.split(r'[.!?]', summary) if s.strip()]
        
        # If not enough sentences, return the original summary
        if len(sentences) < 1:
            return summary
            
        # Ensure we have at least 3 points by repeating or generating generic ones
        points = []
        for sentence in sentences:
            # Ensure the sentence has substance (at least 15 chars) and isn't promotional
            if len(sentence) > 15 and not self._is_generic_sentence(sentence) and not self._is_promotional(sentence):
                # Capitalize first letter and ensure proper formatting
                formatted_sentence = sentence[0].upper() + sentence[1:]
                if formatted_sentence[-1] not in ['.', '!', '?']:
                    formatted_sentence += ''
                points.append(formatted_sentence)
        
        # If we don't have enough points, extract more from the content directly
        if len(points) < 3 and stock_info["content"]:
            content_points = self._extract_points_from_content(stock_info["content"], stock_info["symbol"])
            for point in content_points:
                if point not in points and len(points) < 3 and not self._is_promotional(point):
                    points.append(point)
        
        # If still not enough points, add generic ones based on context
        symbol = stock_info["symbol"] if stock_info["symbol"] else "the company"
        
        generic_up_points = [
            f"Strong financial performance from {symbol}",
            f"Positive market sentiment surrounding {symbol}",
            f"Favorable industry trends benefiting {symbol}"
        ]
        
        generic_down_points = [
            f"Weaker than expected financial results from {symbol}",
            f"Negative market sentiment affecting {symbol}",
            f"Industry challenges impacting {symbol}"
        ]
        
        while len(points) < 3:
            if stock_info["direction"] == "up":
                points.append(generic_up_points[len(points) % 3])
            else:
                points.append(generic_down_points[len(points) % 3])
        
        # Format using appropriate template - take only up to 3 most relevant points
        if stock_info["direction"] == "up":
            return STOCK_UP_TEMPLATE.format(
                symbol=stock_info["symbol"] if stock_info["symbol"] else "the stock",
                point1=points[0],
                point2=points[1],
                point3=points[2]
            )
        else:
            return STOCK_DOWN_TEMPLATE.format(
                symbol=stock_info["symbol"] if stock_info["symbol"] else "the stock",
                point1=points[0],
                point2=points[1],
                point3=points[2]
            )
    
    def _is_promotional(self, sentence):
        """Check if a sentence contains promotional content"""
        promo_phrases = [
            "unlock stock picks", 
            "broker level", 
            "broker-level", 
            "newsfeed that powers", 
            "wall street", 
            "subscribe",
            "premium content",
            "register for",
            "sign up for"
        ]
        
        sentence_lower = sentence.lower()
        for phrase in promo_phrases:
            if phrase in sentence_lower:
                return True
        return False
    
    def _is_generic_sentence(self, sentence):
        """Check if a sentence is too generic to be useful"""
        generic_patterns = [
            r"based on.*information",
            r"the stock.*moving",
            r"regarding.*stock",
            r"this summarizes",
            r"these factors.*stock",
            r"these.*factors",
            r"the stock.*affected",
            r"the following.*factors",
            r"key factors.*stock",
            r"these are.*factors"
        ]
        
        sentence = sentence.lower()
        for pattern in generic_patterns:
            if re.search(pattern, sentence):
                return True
        return False
    
    def _extract_points_from_content(self, content, symbol):
        """Extract specific points directly from the content"""
        points = []
        
        # Look for sentences containing the symbol or stock-relevant terms
        relevant_terms = [symbol.lower(), "revenue", "earnings", "profit", "loss", 
                         "announced", "reported", "launched", "released", 
                         "increased", "decreased", "growth", "decline",
                         "market", "investor", "product"]
        
        # Split content into sentences
        content_sentences = [s.strip() for s in re.split(r'[.!?]', content) if s.strip()]
        
        for sentence in content_sentences:
            sentence_lower = sentence.lower()
            if any(term in sentence_lower for term in relevant_terms) and not self._is_promotional(sentence):
                # Format the sentence properly
                if len(sentence) > 15:
                    formatted = sentence[0].upper() + sentence[1:]
                    if formatted[-1] not in ['.', '!', '?']:
                        formatted += ''
                    points.append(formatted)
        
        return points
    
    def _clean_redundant_sentences(self, text):
        """Remove redundant sentences that might appear in the model output"""
        sentences = text.split('. ')
        if len(sentences) <= 2:
            return text
            
        # Check for redundancy by comparing sentence similarity
        unique_sentences = []
        for sentence in sentences:
            if sentence and not self._is_promotional(sentence) and not any(self._is_similar_sentence(sentence, existing) for existing in unique_sentences):
                unique_sentences.append(sentence)
        
        # Reconstruct the text
        cleaned_text = '. '.join(unique_sentences)
        if not cleaned_text.endswith('.') and text.endswith('.'):
            cleaned_text += '.'
            
        return cleaned_text
    
    def _is_similar_sentence(self, sentence1, sentence2):
        """Check if two sentences are similar using basic string comparison"""
        # Convert to lowercase and remove punctuation for comparison
        s1 = ''.join(c.lower() for c in sentence1 if c.isalnum() or c.isspace())
        s2 = ''.join(c.lower() for c in sentence2 if c.isalnum() or c.isspace())
        
        # If one is contained in the other or they share over 80% of words
        words1 = set(s1.split())
        words2 = set(s2.split())
        
        # Check if one is a subset of the other
        if words1.issubset(words2) or words2.issubset(words1):
            return True
            
        # Check word overlap ratio
        if len(words1) == 0 or len(words2) == 0:
            return False
            
        overlap = len(words1.intersection(words2))
        smaller_set = min(len(words1), len(words2))
        if smaller_set > 0 and overlap / smaller_set > 0.8:
            return True
            
        return False
    
    def _clean_prompt(self, prompt):
        """Clean and format the prompt for summarization"""
        # Extract stock info
        stock_info = self._extract_stock_info(prompt)
        
        # For stock analysis prompts, extract the important parts
        if stock_info["is_stock_query"]:
            # Create a clear prompt for the model to understand
            symbol_text = f"for {stock_info['symbol']}" if stock_info["symbol"] else ""
            direction_text = f"{'positive' if stock_info['direction'] == 'up' else 'negative'}" if stock_info["direction"] else ""
            content = stock_info["content"] if stock_info["content"] else ""
            
            # Create a simple and direct prompt
            if content:
                return f"List the three most important factors affecting stock price {symbol_text} {direction_text} based on: {content}"
            else:
                return f"List three factors affecting stock price {symbol_text} {direction_text}"
        
        return prompt
    
    def _generate_fallback(self, prompt, stock_info=None):
        """Generate a reasonable default summary without using the model"""
        logger.info("Using fallback text generation mechanism")
        
        if stock_info is None:
            stock_info = self._extract_stock_info(prompt)
        
        # Check if it's a stock summary request
        if stock_info["is_stock_query"]:
            symbol = stock_info["symbol"] if stock_info["symbol"] else "the company"
            
            if stock_info["direction"] == "up":
                return STOCK_UP_TEMPLATE.format(
                    symbol=symbol,
                    point1=f"Strong financial performance and positive earnings",
                    point2=f"Favorable market conditions and investor sentiment",
                    point3=f"Strategic initiatives and innovation driving growth"
                )
            else:
                return STOCK_DOWN_TEMPLATE.format(
                    symbol=symbol,
                    point1=f"Weaker than expected financial results",
                    point2=f"Negative market sentiment affecting valuation",
                    point3=f"Industry challenges and competitive pressures"
                )
            
        # Generic fallback
        return "The information suggests implications for financial markets and stock performance, with several factors influencing investor decisions." 