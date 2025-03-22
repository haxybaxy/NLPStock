from dotenv import load_dotenv
from groq import Groq
from transformers import pipeline
import os
import time


load_dotenv()

GROQ_API_KEY_1 = os.getenv("GROQ_API_KEY_1")
GROQ_API_KEY_2 = os.getenv("GROQ_API_KEY_2")

# Alternating between two API keys between every call
class GroqClientManager:
    def __init__(self, api_key_1, api_key_2):
        self.api_keys = [api_key_1, api_key_2]
        self.current_key_index = 0

    def get_client(self):
        # Get the current Groq client based on active API key
        api_key = self.api_keys[self.current_key_index]
        return Groq(api_key=api_key)

    def switch_key(self):
        # Switch to the other API key
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)

groq_manager = GroqClientManager(GROQ_API_KEY_1, GROQ_API_KEY_2)
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

def retry(func, **kwargs):
    try:
        return func(**kwargs)
    except Exception as e:
        if "rate_limit_exceeded" in str(e):
            time.sleep(120)
            return func(**kwargs)
        else:
            raise


def send_prompt(prompt: str):
    response = groq_manager.get_client().chat.completions.create(model="llama3-8b-8192", messages=[{"role": "user", "content": prompt}])
    return response.choices[0].message.content


def summarize_article(article_text, symbol, direction):
    if article_text == "Full article text not found.":
        return None

    max_chunk_size = 2048
    article_chunks = [article_text[i : i + max_chunk_size] for i in range(0, len(article_text), max_chunk_size)]

    summaries = []
    for chunk in article_chunks:
        prompt = (
            f"Act as a financial analyst and in one sentence explain the specific reasons why the stock {symbol} moved {direction} based on: {chunk}. Avoid saying you're a financial analyst and provide specific reasons rather than generic."
        )
        
        try:
            content = retry(send_prompt, prompt=prompt)
            summaries.append(content)
        except (KeyError, TypeError, AttributeError) as e:
            summaries.append(f"Error parsing response: {e}")
        groq_manager.switch_key()

    return " ".join(summaries)


def summarize_articles(articles, symbol):
    valid_articles = [article for article in articles if article]
    if not valid_articles:
        return "No valid articles found."

    combined_summaries = "\n\n".join(valid_articles)
    prompt = (
        f"Summarize the following news and write an informative paragraph explaining why the stock {symbol} is moving. Avoid using phrases like 'several factors' or 'combination of factors' and eliminate unrelated content, don't say this is a summary: {combined_summaries}"
    )

    try:
        summary = retry(send_prompt, prompt=prompt)
    except (KeyError, TypeError, AttributeError) as e:
        summary = f"Error parsing response: {e}"
    groq_manager.switch_key()

    final_summary_result = summarizer(summary, max_length=100, min_length=60, do_sample=False)
    if isinstance(final_summary_result, list):
        final_summary = final_summary_result[0]["summary_text"]
    else:
        final_summary = "Error generating summary"

    # Post-process to remove sentences with unwanted phrases
    phrases_to_avoid = ["several factors", "combination of factors", "various factors"]
    sentences = final_summary.split(". ")
    filtered_sentences = [
        sentence for sentence in sentences if not any(phrase in sentence for phrase in phrases_to_avoid)
    ]
    final_summary = ". ".join(filtered_sentences)

    return final_summary
