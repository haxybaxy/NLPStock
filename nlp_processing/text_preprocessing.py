import re
import string
import logging
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import WordNetLemmatizer

logger = logging.getLogger(__name__)

# Download NLTK resources if not already downloaded
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('wordnet')

# Financial keywords that might indicate stock movement
FINANCIAL_KEYWORDS = [
    'earnings', 'revenue', 'profit', 'loss', 'guidance', 'forecast', 'outlook', 
    'dividend', 'acquisition', 'merger', 'buyback', 'restructuring', 'layoff',
    'lawsuit', 'settlement', 'regulation', 'investigation', 'approval', 'launch',
    'patent', 'contract', 'partnership', 'investment', 'debt', 'bankruptcy',
    'downgrade', 'upgrade', 'target', 'rating', 'analyst', 'quarterly', 'annual',
    'growth', 'decline', 'beat', 'miss', 'exceed', 'below', 'above', 'estimate',
    'expectation', 'surprise', 'guidance', 'CEO', 'executive', 'management',
    'board', 'director', 'shareholder', 'investor', 'stake', 'share', 'stock',
    'market', 'trading', 'volatility', 'volume', 'price', 'valuation', 'multiple',
    'ratio', 'EPS', 'P/E', 'revenue', 'sales', 'margin', 'cost', 'expense',
    'capital', 'cash', 'flow', 'balance', 'sheet', 'asset', 'liability'
]

def preprocess_text(text):
    """Preprocess text by removing stopwords, punctuation, and lemmatizing"""
    if text == "Full article text not found." or not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove punctuation
    text = text.translate(str.maketrans('', '', string.punctuation))
    
    # Tokenize
    tokens = word_tokenize(text)
    
    # Remove stopwords
    stop_words = set(stopwords.words('english'))
    tokens = [token for token in tokens if token not in stop_words]
    
    # Lemmatize
    lemmatizer = WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(token) for token in tokens]
    
    return ' '.join(tokens)

def extract_key_sentences(text, company_name, ticker, top_n=10):
    """Extract key sentences from the article text"""
    if text == "Full article text not found." or not text:
        return ""
    
    # Normalize company name and ticker for case-insensitive matching
    company_name_lower = company_name.lower()
    ticker_lower = ticker.lower()
    
    # Split into sentences
    sentences = sent_tokenize(text)
    
    # Score sentences based on relevance
    scored_sentences = []
    for sentence in sentences:
        score = 0
        
        # Check for company name and ticker
        if company_name_lower in sentence.lower():
            score += 3
        if ticker_lower in sentence.lower():
            score += 2
            
        # Check for financial keywords
        for keyword in FINANCIAL_KEYWORDS:
            if keyword.lower() in sentence.lower():
                score += 1
                
        # Check for numbers (potential financial figures)
        if re.search(r'\d+\.?\d*%?', sentence):
            score += 1
            
        # Check for dollar amounts
        if re.search(r'\$\d+\.?\d*|\d+\.?\d*\s+dollars', sentence):
            score += 2
            
        scored_sentences.append((sentence, score))
    
    # Sort by score and take top N
    scored_sentences.sort(key=lambda x: x[1], reverse=True)
    top_sentences = [sentence for sentence, score in scored_sentences[:top_n]]
    
    return " ".join(top_sentences) 