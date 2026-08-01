# src/utils/thai_cleaner.py
import re
from pythainlp.util import normalize
from pythainlp.tokenize import word_tokenize

class ThaiCleaner:
    def __init__(self):
        # Regex to remove common "social media noise"
        self.url_pattern = re.compile(r'https?://\S+|www\.\S+')
        self.mention_pattern = re.compile(r'@\w+')
        self.hashtag_pattern = re.compile(r'#\w+')
        # Regex to reduce repeating characters (e.g., มากกกก -> มาก)
        self.repeat_char_pattern = re.compile(r'(.)\1{2,}') 

    def clean(self, text: str) -> str:
        """
        Master cleaning function for Thai text.
        """
        if not text or not isinstance(text, str):
            return ""

        # 1. Remove URLs, Mentions, Hashtags (Standard Noise)
        text = self.url_pattern.sub('', text)
        text = self.mention_pattern.sub('', text)
        text = self.hashtag_pattern.sub('', text)

        # 2. PyThaiNLP Normalization
        # This fixes floating vowels and reorders tone marks standardly
        text = normalize(text)

        # 3. Reduce repeating characters (Social media emphasis)
        # Replaces 3+ repeating chars with just 1 (e.g., 55555 -> 5)
        # Note: In a real project, you might want to keep '555' as 'LOL'
        text = self.repeat_char_pattern.sub(r'\1', text)

        # 4. Strip whitespace
        text = text.strip()

        return text

    def tokenize(self, text: str) -> list:
        """
        Wrapper for PyThaiNLP's word_tokenize using 'newmm' (dictionary-based).
        Good for general purpose.
        """
        cleaned_text = self.clean(text)
        return word_tokenize(cleaned_text, engine="newmm")

# --- Quick Test Block (Runs only if you execute this file directly) ---
if __name__ == "__main__":
    cleaner = ThaiCleaner()
    raw_text = "สวัสดีครับบบ!!! https://test.com วันนี้อากาศดีมากกกก #bkk"
    print(f"Original: {raw_text}")
    print(f"Cleaned:  {cleaner.clean(raw_text)}")
    print(f"Tokens:   {cleaner.tokenize(raw_text)}")