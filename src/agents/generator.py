# src/agents/generator.py
from typing import Optional

class ConstitutionalGenerator:
    def __init__(self, model_client=None):
        """
        The Writer Agent. It drafts professional Thai text and refines it based on feedback.
        """
        self.client = model_client

    def generate_draft(self, informal_text: str) -> str:
        """
        Step 1: Attempt to rewrite the informal text to professional Thai.
        """
        prompt = f"""
        You are a professional Thai secretary. Rewrite the following informal text 
        into polite business Thai (Formal Register).
        
        Input: "{informal_text}"
        
        Output only the rewritten Thai text.
        """
        # In a real app, you would call: self.client.chat.completions.create(...)
        return self.mock_generate(informal_text, "draft")

    def revise_draft(self, original_text: str, current_draft: str, critique: str) -> str:
        """
        Step 2: Fix the draft based on the Constitutional Judge's critique.
        """
        prompt = f"""
        Original Input: "{original_text}"
        Current Draft: "{current_draft}"
        Critique from Senior Editor: "{critique}"
        
        Task: Rewrite the draft to address the critique. Ensure you fix specific issues 
        like missing particles or wrong pronouns.
        
        Output only the revised Thai text.
        """
        return self.mock_generate(current_draft, "revision")

    def mock_generate(self, input_text: str, mode: str) -> str:
        """
        MOCK logic to simulate an LLM's response.
        """
        if mode == "draft":
            # Simulates a naive first attempt (good vocab, but maybe missing a particle)
            return "ผมไม่ว่างครับ ต้องไปทำธุระ" 
        
        if mode == "revision":
            # Simulates fixing the issue after critique
            return "ขออภัยด้วยครับ ช่วงนี้ผมติดภารกิจสำคัญ อาจจะไม่สะดวกครับ"

# --- Quick Test Block ---
if __name__ == "__main__":
    writer = ConstitutionalGenerator()
    
    # 1. Draft
    raw = "mai wang, pai tham thura"
    draft = writer.generate_draft(raw)
    print(f"Draft: {draft}")
    
    # 2. Simulate a Critique (pretend the Judge sent this)
    critique = "Too direct. Use 'Apologize' and 'Mission' instead of just 'Busy'."
    
    # 3. Revision
    final = writer.revise_draft(raw, draft, critique)
    print(f"Final: {final}")