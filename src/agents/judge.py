# src/agents/judge.py
import json
import re
from typing import Dict, Any
from .constitution import ThaiConstitution

class ConstitutionalJudge:
    def __init__(self, model_client=None):
        """
        The Judge Agent that evaluates Thai text against the Constitution.
        :param model_client: A wrapper for your LLM provider (e.g., OpenAI, vLLM).
        """
        self.system_prompt = ThaiConstitution.SYSTEM_PROMPT
        self.rubric = ThaiConstitution.get_rubric()
        self.client = model_client

    def construct_critique_prompt(self, original_text: str, candidate_text: str) -> str:
        """
        Creates the prompt that forces the LLM to act as the Royal Institute expert.
        """
        prompt = f"""
        [Original Informal Text]: "{original_text}"
        [Candidate Professional Text]: "{candidate_text}"

        Review the [Candidate Professional Text] based on the 5 Pillars of Professionalism.
        
        Rubric Reference:
        {json.dumps(self.rubric, indent=2, ensure_ascii=False)}

        Output strictly in this JSON format:
        {{
            "score": <int 1-5>,
            "critique": "<Specific feedback citing the pillars>",
            "missing_particles": <bool>,
            "wrong_pronouns": <bool>
        }}
        """
        return prompt

    def mock_evaluate(self, original_text: str, candidate_text: str) -> Dict[str, Any]:
        """
        A MOCK evaluation to test the pipeline without spending API credits yet.
        Simulates what a real LLM Judge would return.
        """
        # Simple rule-based heuristics for the 'mock' judge
        score = 3
        critique = "Polite but could be more formal."
        
        # Check for particles (The 'Particle Rule')
        if not any(p in candidate_text for p in ["ครับ", "ค่ะ"]):
            score = 1
            critique = "CRITICAL: Missing polite particle (Krub/Ka)."
        
        # Check for informal pronouns
        if "เรา" in candidate_text or "กู" in candidate_text:
            score = 2
            critique = "Found informal pronouns (Rao/Guu). Use 'Phom' or 'Dichan'."

        return {
            "score": score,
            "critique": critique,
            "original": original_text,
            "candidate": candidate_text
        }

# --- Quick Test Block ---
if __name__ == "__main__":
    judge = ConstitutionalJudge()
    
    # Test Case 1: Bad (No particle, informal pronoun)
    print("--- Test Case 1: Informal ---")
    result_bad = judge.mock_evaluate("im busy", "เรายุ่งมาก")
    print(json.dumps(result_bad, indent=2, ensure_ascii=False))

    # Test Case 2: Good (Formal)
    print("\n--- Test Case 2: Formal ---")
    result_good = judge.mock_evaluate("im busy", "ขอโทษครับ ช่วงนี้ผมติดภารกิจครับ")
    print(json.dumps(result_good, indent=2, ensure_ascii=False))