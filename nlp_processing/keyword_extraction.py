import logging
from collections import Counter
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import yake

logger = logging.getLogger(__name__)

def extract_keywords(text, max_keywords=10):
    """Extract keywords using YAKE"""
    if text == "Full article text not found." or not text:
        return []
    
    try:
        kw_extractor = yake.KeywordExtractor(
            lan="en", 
            n=2,  # ngram size
            dedupLim=0.9,  # deduplication threshold
            dedupFunc='seqm',  # deduplication function
            windowsSize=1,  # window size
            top=max_keywords  # number of keywords to extract
        )
        keywords = kw_extractor.extract_keywords(text)
        return [kw[0] for kw in keywords]  # Return just the keywords, not the scores
    except Exception as e:
        logger.warning(f"YAKE keyword extraction failed: {e}. Falling back to frequency-based extraction.")
        # Fallback to simple frequency-based extraction
        words = word_tokenize(text.lower())
        stop_words = set(stopwords.words('english'))
        words = [word for word in words if word.isalpha() and word not in stop_words]
        
        word_freq = Counter(words)
        return [word for word, freq in word_freq.most_common(max_keywords)] 