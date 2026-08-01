# src/pipeline.py
import json
import time
from typing import List, Dict
from src.agents.judge import ConstitutionalJudge
from src.agents.generator import ConstitutionalGenerator
from src.utils.thai_cleaner import ThaiCleaner

class SawasdeePipeline:
    def __init__(self):
        """
        The Orchestrator. Connects the Writer (Generator) and the Editor (Judge)
        to produce high-quality DPO training pairs automatically.
        """
        self.cleaner = ThaiCleaner()
        self.judge = ConstitutionalJudge()
        self.generator = ConstitutionalGenerator()

    def process_single_item(self, raw_input: str) -> Dict:
        """
        Runs the full RLAIF loop for a single piece of text.
        Returns a dictionary formatted for DPO training.
        """
        # 1. Clean the Input
        clean_input = self.cleaner.clean(raw_input)
        print(f"--- Processing: {clean_input[:30]}... ---")

        # 2. Agent A: Generate Initial Draft (The "Rejected" Candidate)
        draft = self.generator.generate_draft(clean_input)
        
        # 3. Agent B: Judge the Draft
        # In a real loop, we check if the draft is already perfect. 
        # If it's perfect, we might skip revision. Here we force revision for data.
        critique_data = self.judge.mock_evaluate(clean_input, draft)
        print(f"   [Judge]: Score {critique_data['score']} - {critique_data['critique']}")

        # 4. Agent A: Revise based on Critique (The "Chosen" Candidate)
        final_version = self.generator.revise_draft(
            clean_input, 
            draft, 
            critique_data['critique']
        )
        print(f"   [Revision]: {final_version}")

        # 5. Format for DPO (Standard HuggingFace Format)
        # We assume the 'final_version' is better than 'draft' because it followed the critique.
        dpo_entry = {
            "prompt": clean_input,
            "chosen": final_version,   # The revised, polite version
            "rejected": draft,         # The initial, potentially flawed version
            "meta": {
                "initial_score": critique_data['score'],
                "critique": critique_data['critique']
            }
        }
        return dpo_entry

    def run_batch(self, raw_texts: List[str], output_file: str):
        """
        Processes a list of raw Thai texts and saves the dataset to JSONL.
        """
        dataset = []
        for text in raw_texts:
            try:
                entry = self.process_single_item(text)
                dataset.append(entry)
                # Slight delay to simulate API calls
                time.sleep(0.5) 
            except Exception as e:
                print(f"Error processing '{text}': {e}")

        # Save to JSONL (The standard format for AI training)
        with open(output_file, 'w', encoding='utf-8') as f:
            for entry in dataset:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        print(f"\n[Success] Saved {len(dataset)} DPO pairs to {output_file}")

# --- Execution Block ---
if __name__ == "__main__":
    pipeline = SawasdeePipeline()

    # 1. Simulate some raw "Social Media" data
    raw_social_data = [
        "meeting 5pm mai dai na, busy mak",
        "send file hai noi kub, urgent!!!!",
        "kor thod tee, leum wa mee meeting",
        "rak na jub jub 55555"
    ]

    # 2. Run the Factory
    output_path = "data/sawasdee_dpo_pairs_v1.jsonl"
    pipeline.run_batch(raw_social_data, output_path)