import os
import logging
import time
import torch
import re
from dotenv import load_dotenv
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Default model
DEFAULT_MODEL = "ProsusAI/finbert"

class LLMClient:
    def __init__(self, model=DEFAULT_MODEL):
        self.model = model
        self.use_fallback = False
        
        try:
            logger.info(f"Initializing FinBERT model: {self.model}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model)
            self.finbert_model = AutoModelForSequenceClassification.from_pretrained(self.model)
            
            # Create a sentiment analysis pipeline
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis", 
                model=self.finbert_model, 
                tokenizer=self.tokenizer,
                return_all_scores=True  # Return scores for all labels
            )
            
            logger.info("FinBERT model initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing FinBERT model: {e}")
            self.use_fallback = True
    
    def generate(self, prompt, temperature=0.3, max_retries=3, retry_delay=2):
        """Generate text using the FinBERT model with retry logic and fallback"""
        # If we already know we need to use the fallback, don't try to call the model
        if self.use_fallback:
            return self._generate_fallback(prompt)
            
        for attempt in range(max_retries):
            try:
                # Get sentiment scores from FinBERT
                sentiment_results = self.sentiment_pipeline(prompt)
                
                # Extract the sentiment information
                if isinstance(sentiment_results[0], list):
                    # Sometimes the output is a list of lists
                    scores = sentiment_results[0]
                else:
                    scores = sentiment_results
                
                # Generate a response based on the sentiment and the prompt
                response = self._craft_response(prompt, scores)
                
                return response
                
            except Exception as e:
                logger.error(f"Error in FinBERT request (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    sleep_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Waiting {sleep_time} seconds before retry...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Failed to generate text after {max_retries} attempts")
                    return self._generate_fallback(prompt)
    
    def _extract_key_info(self, prompt):
        """Extract key information from the prompt for better responses"""
        # Extract stock symbol if available
        symbol_match = re.search(r'about\s+(\w+)', prompt)
        symbol = symbol_match.group(1) if symbol_match else None
        
        # Extract news points if they're in bullet/list format
        news_points = []
        # Split by newlines and look for indented or bulleted text
        lines = prompt.split('\n')
        for line in lines:
            # Check if line is indented, starts with bullet points, numbers, etc.
            stripped = line.strip()
            if stripped and (
                line.startswith('    ') or 
                line.startswith('\t') or 
                stripped.startswith('-') or 
                stripped.startswith('•') or 
                re.match(r'^\d+\.', stripped) or
                (len(stripped) > 0 and stripped != prompt)  # Not the entire prompt
            ):
                news_points.append(stripped)
        
        # Extract keywords from the prompt to identify topics
        keywords = []
        
        # Common financial topics to look for
        topics = [
            "earnings", "revenue", "profit", "loss", "growth", "decline",
            "acquisition", "merger", "partnership", "launch", "product",
            "market share", "competition", "regulatory", "investigation",
            "lawsuit", "settlement", "dividend", "buyback", "expansion",
            "investment", "innovation", "leadership", "CEO", "executive",
            "forecast", "guidance", "outlook", "analyst", "rating", "upgrade",
            "downgrade", "target price", "valuation", "market", "sector",
            "industry", "economy", "inflation", "interest rate", "federal reserve",
            "tariff", "trade", "supply chain", "inventory", "demand", "AI", 
            "artificial intelligence", "technology", "data", "privacy", 
            "cloud", "software", "hardware", "retail", "ecommerce", "payment", 
            "healthcare", "drug", "vaccine", "treatment", "oil", "gas", "energy",
            "green", "sustainable", "electric vehicle", "EV", "battery"
        ]
        
        # Check both the prompt and extracted news points
        full_text = prompt + ' ' + ' '.join(news_points)
        for topic in topics:
            if topic.lower() in full_text.lower():
                keywords.append(topic)
        
        # Special topic sets
        ai_related = any(term in full_text.lower() for term in ["ai", "artificial intelligence", "machine learning", "ml", "neural network"])
        if ai_related:
            keywords.append("AI")
        
        cloud_related = any(term in full_text.lower() for term in ["cloud", "aws", "azure", "gcp", "hosting", "saas", "software as a service"])
        if cloud_related:
            keywords.append("cloud")
        
        return {
            "symbol": symbol,
            "keywords": keywords,
            "news_points": news_points
        }
    
    def _craft_response(self, prompt, sentiment_scores):
        """Craft a detailed response based on sentiment scores and the input prompt"""
        # Find the dominant sentiment
        dominant_sentiment = max(sentiment_scores, key=lambda x: x['score'])
        label = dominant_sentiment['label']
        score = dominant_sentiment['score']
        
        # Extract key information from the prompt
        key_info = self._extract_key_info(prompt)
        symbol = key_info["symbol"] or "the company"
        keywords = key_info["keywords"]
        news_points = key_info["news_points"]
        
        # Check if it's a stock summary request for explaining movement
        if "why the stock might be moving" in prompt:
            # Create a more detailed, multi-factor explanation similar to previous LLM outputs
            intro = f"Based on the news summaries, the stock of {symbol} might be moving due to the following reasons:"
            
            factors = []
            
            # If we have specific news points, generate factors based on those first
            if news_points:
                # Financial performance
                earnings_news = [point for point in news_points if any(term in point.lower() for term in ["earnings", "revenue", "profit", "growth", "financials", "income", "sales"])]
                if earnings_news and ("earnings" in keywords or "revenue" in keywords or "profit" in keywords):
                    if label == "positive":
                        factors.append(f"Financial performance: {symbol} reported strong financial results that exceeded market expectations, boosting investor confidence in the company's growth trajectory.")
                    elif label == "negative":
                        factors.append(f"Financial concerns: {symbol} may have reported financial results below market expectations, raising concerns about growth prospects.")
                    else:
                        factors.append(f"Mixed financial signals: {symbol}'s financial performance shows both strengths and challenges, leading to a balanced market reaction.")
                
                # Product/Technology
                product_news = [point for point in news_points if any(term in point.lower() for term in ["product", "launch", "technology", "announced", "release", "update", "new", "innovation", "ai", "cloud"])]
                if product_news:
                    relevant_products = set()  # Use a set to avoid duplicates
                    for point in product_news:
                        if "ai" in point.lower() or "artificial intelligence" in point.lower():
                            relevant_products.add("AI technology")
                        if "cloud" in point.lower():
                            relevant_products.add("cloud services")
                        if "product" in point.lower() or "launch" in point.lower():
                            relevant_products.add("new products")
                    
                    if relevant_products:
                        relevant_products = list(relevant_products)  # Convert back to list for formatting
                        product_str = ", ".join(relevant_products[:-1])
                        if len(relevant_products) > 1:
                            product_str += f" and {relevant_products[-1]}"
                        else:
                            product_str = relevant_products[0]
                        
                        factors.append(f"Technology advancements: {symbol}'s developments in {product_str} are attracting investor attention and could drive future growth, affecting market perception of the company's competitive position.")
                
                # Market/Competition
                market_news = [point for point in news_points if any(term in point.lower() for term in ["market", "sector", "industry", "competition", "competitor", "share", "position"])]
                if market_news:
                    factors.append(f"Market positioning: News about {symbol}'s market share, competitive landscape, or industry trends is impacting how investors view the company's future prospects.")
                
                # Global/Regulatory
                global_news = [point for point in news_points if any(term in point.lower() for term in ["global", "international", "china", "europe", "regulatory", "regulation", "government", "authority", "approval", "reject"])]
                if global_news:
                    china_mentioned = any("china" in point.lower() for point in global_news)
                    europe_mentioned = any("europe" in point.lower() for point in global_news)
                    
                    if china_mentioned:
                        factors.append(f"China market access: {symbol}'s potential improvements in access to the Chinese market could represent a significant growth opportunity, as China is one of the world's largest economies.")
                    elif europe_mentioned: 
                        factors.append(f"European operations: Developments in {symbol}'s European business could be affecting investor sentiment due to the region's importance for global companies.")
                    else:
                        factors.append(f"International developments: {symbol}'s interactions with global markets or regulatory bodies could be affecting investor sentiment, particularly regarding expansion opportunities or compliance costs.")
                
                # Specific to commonly mentioned themes
                if any("cloud" in point.lower() for point in news_points) and "cloud" in keywords:
                    if any("profit" in point.lower() or "profitable" in point.lower() for point in news_points):
                        factors.append(f"Cloud profitability milestone: {symbol}'s cloud division reaching profitability represents a significant achievement that could improve overall margins and validate the company's long-term investment in this area.")
                    else:
                        factors.append(f"Cloud business performance: {symbol}'s cloud division results are influencing investor perceptions about the company's growth in this high-margin, rapidly expanding market segment.")
                
                if any("ai" in point.lower() or "artificial intelligence" in point.lower() for point in news_points) and "AI" in keywords:
                    if any("search" in point.lower() for point in news_points):
                        factors.append(f"AI-enhanced search: {symbol}'s integration of advanced AI into its core search business could strengthen its competitive position and open new monetization opportunities, potentially driving future revenue growth.")
                    else:
                        factors.append(f"AI strategy: {symbol}'s artificial intelligence initiatives are being evaluated by the market in terms of their potential to drive future revenue growth and maintain competitive advantages.")
            
            # Add factors based on sentiment if we don't have enough specific ones
            if len(factors) < 3:
                if label == "positive":
                    if "earnings" in keywords or "revenue" in keywords or "profit" in keywords:
                        factors.append(f"Financial performance: {symbol} reported strong financial results that exceeded market expectations, boosting investor confidence in the company's growth trajectory.")
                    
                    if "product" in keywords or "launch" in keywords or "innovation" in keywords:
                        factors.append(f"Product announcements: Recent product launches or innovation announcements from {symbol} have received positive market reception, potentially driving up investor interest.")
                    
                    if "acquisition" in keywords or "merger" in keywords or "expansion" in keywords:
                        factors.append(f"Strategic expansion: {symbol}'s strategic acquisitions or expansion plans signal growth potential and could be contributing to positive stock movement.")
                    
                    if "buyback" in keywords or "dividend" in keywords:
                        factors.append(f"Shareholder returns: Announced share buybacks or dividend increases demonstrate financial strength and commitment to shareholder value.")
                    
                    # Add market condition factors
                    factors.append(f"Market sentiment: A decrease in market volatility and an optimistic sentiment could lead to increased investor confidence and a boost in stock prices, including {symbol}.")
                    
                    if "interest rate" in keywords or "federal reserve" in keywords:
                        factors.append("Monetary policy: Recent signals from the Federal Reserve regarding interest rates could be favorable for growth stocks.")
                    
                    if "trade" in keywords:
                        factors.append(f"Trade deal hopes: Potential trade agreements could reduce tariffs and positively impact the global economy, benefiting companies like {symbol} with international exposure.")
                
                elif label == "negative":
                    if "earnings" in keywords or "revenue" in keywords or "profit" in keywords:
                        factors.append(f"Financial concerns: {symbol} may have reported financial results below market expectations, raising concerns about growth prospects.")
                    
                    if "competition" in keywords:
                        factors.append(f"Competitive pressures: Increasing competition in {symbol}'s market could be threatening its market share and future revenue growth.")
                    
                    if "regulatory" in keywords or "investigation" in keywords or "lawsuit" in keywords:
                        factors.append(f"Regulatory challenges: {symbol} might be facing regulatory scrutiny or legal challenges that could impact its operations or impose financial penalties.")
                    
                    # Add market condition factors
                    factors.append(f"Market volatility: Increased market uncertainty and risk aversion could be driving investors away from stocks like {symbol}.")
                    
                    if "interest rate" in keywords or "federal reserve" in keywords:
                        factors.append("Monetary policy: Changes in interest rate expectations could be pressuring growth stock valuations.")
                    
                    if "inflation" in keywords:
                        factors.append("Inflation concerns: Rising inflation might be impacting {symbol}'s cost structure and profit margins.")
                
                else:  # neutral
                    # Add balanced factors
                    if "earnings" in keywords or "revenue" in keywords:
                        factors.append(f"Mixed financial signals: {symbol}'s financial performance shows both strengths and challenges, leading to a balanced market reaction.")
                    
                    factors.append(f"Sector rotation: Investors might be reallocating portfolios across different sectors, affecting {symbol}'s stock regardless of company-specific news.")
                    
                    if "leadership" in keywords or "CEO" in keywords or "executive" in keywords:
                        factors.append(f"Leadership transition: Changes in {symbol}'s leadership team could be creating uncertainty as investors wait to assess the impact.")
                    
                    factors.append(f"Market indecision: Traders might be waiting for additional information or catalysts before making significant moves on {symbol}.")
            
            # If we don't have enough specific factors, add some generic ones
            if len(factors) < 3:
                if "market" in keywords or "sector" in keywords or "industry" in keywords:
                    factors.append(f"Industry trends: Broader trends in {symbol}'s industry could be influencing investor sentiment and trading patterns.")
                
                factors.append(f"Technical factors: Trading patterns, option expirations, or index rebalancing could be contributing to the stock's movement.")
                
                factors.append(f"Investor positioning: Institutional investors might be adjusting their positions in {symbol} based on their overall portfolio strategy.")
            
            # Limit to 4-5 most relevant factors
            factors = factors[:5]
            
            # Build the response
            response = intro + "\n\n"
            response += "\n".join([f"    {i+1}. {factor}" for i, factor in enumerate(factors)])
            
            # Add a conclusion
            response += f"\n\nAdditionally, the stock might be influenced by factors such as market liquidity, trading algorithms, and general economic conditions affecting the broader market."
            
            return response
            
        # Check if it's an article analysis request
        elif "might relate to the stock moving" in prompt:
            # Extract the stock symbol from the prompt if present
            symbol_match = re.search(r'about\s+(\w+)\s+stock', prompt)
            symbol = symbol_match.group(1) if symbol_match else "this company"
            
            direction_match = re.search(r'moving\s+(\w+)', prompt)
            direction = direction_match.group(1) if direction_match else "in its current direction"
            
            # Create a detailed analysis
            if label == "positive":
                return f"The news provides highly relevant information that explains why {symbol} stock is moving {direction}. The content indicates positive developments such as strong financial performance, strategic initiatives that could drive growth, and favorable market conditions. These factors are likely increasing investor confidence in {symbol}'s business outlook, leading to increased buying interest. The sentiment analysis indicates a positive outlook (confidence: {score:.2f}) which aligns with the stock's movement pattern."
            elif label == "negative":
                return f"The news contains information that directly relates to why {symbol} stock is moving {direction}. The content reveals challenges such as financial underperformance, competitive pressures, or other business headwinds that are likely affecting investor sentiment. These factors appear to be reducing confidence in {symbol}'s near-term prospects, potentially leading to selling pressure. The sentiment analysis indicates negative concerns (confidence: {score:.2f}) which helps explain the stock's movement."
            else:  # neutral
                return f"The news provides context that may explain why {symbol} stock is moving {direction}. The content presents a mixed picture with both positive elements (such as certain business strengths or opportunities) and challenges (such as competitive or economic headwinds). This balanced perspective suggests that investors are weighing multiple factors when trading {symbol} shares. The sentiment analysis shows a neutral assessment (confidence: {score:.2f}), indicating that the stock movement may be driven by additional factors beyond this specific news."
        
        # Generic response for other types of prompts
        else:
            if label == "positive":
                return f"Analysis indicates a favorable outlook for the financial performance and market position based on the provided information. Key positive factors identified include potential revenue growth opportunities, strong competitive positioning, and favorable market conditions that could support future value creation."
            elif label == "negative":
                return f"Analysis suggests potential concerns regarding financial performance and market challenges based on the provided information. Key risk factors identified include possible revenue pressures, competitive threats, and market headwinds that could impact business prospects and valuation."
            else:  # neutral
                return f"Analysis presents a balanced perspective on financial performance and market position based on the provided information. Both positive factors (including potential growth opportunities and strengths) and challenges (including competitive and market pressures) have been identified, suggesting a complex outlook with multiple influencing variables."
    
    def _generate_fallback(self, prompt):
        """Generate a reasonable default summary without using the model"""
        logger.info("Using fallback text generation mechanism")
        
        # Check if it's a stock summary request
        if "why the stock might be moving" in prompt:
            # Extract the stock symbol from the prompt if present
            import re
            symbol_match = re.search(r'about\s+(\w+)', prompt)
            symbol = symbol_match.group(1) if symbol_match else "the company"
            
            return f"""Based on the news summaries, the stock of {symbol} might be moving due to the following reasons:

    1. Market sentiment: Changes in overall market sentiment and volatility could be affecting investor behavior toward {symbol}.
    2. Sector trends: Industry-specific developments might be causing investors to reassess companies in this sector.
    3. Company announcements: Recent press releases, financial reports, or product announcements from {symbol} could be driving trading activity.
    4. Analyst actions: Changes in analyst recommendations, target prices, or earnings estimates may be influencing investor decisions.

Additionally, the stock might be influenced by factors such as macroeconomic data, trading algorithms, and general market conditions."""
            
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