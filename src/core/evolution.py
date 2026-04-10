import random
import time
import json
from typing import List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from src.core.types import SkillGenotype

class EvolutionEngine:
    def __init__(self, meta_model: Optional[BaseChatModel] = None):
        self.meta_model = meta_model

    async def mutate(self, skill: SkillGenotype, feedback: Optional[str] = None) -> SkillGenotype:
        """
        Mutate a skill genotype. If a meta_model is provided, use it to perform
        intelligent prompt engineering based on performance feedback.
        """
        mutation_type = random.random()
        mutated = skill.model_copy()
        mutated.skill_id = f"{skill.skill_id}_mutated_{int(time.time())}"

        if self.meta_model and mutation_type < 0.8:
            # Intelligent LLM-driven mutation
            evolved_prompt = await self._evolve_prompt_with_llm(skill.prompt_chromosome, feedback)
            mutated.prompt_chromosome = evolved_prompt
        elif mutation_type < 0.6:
            # Simple text mutation fallback
            mutated.prompt_chromosome = f"[Optimized] {skill.prompt_chromosome}"
        elif mutation_type < 0.9:
            # Param mutation
            mutated.llm_config.temperature = min(1.0, max(0.0, skill.llm_config.temperature + (random.random() - 0.5) * 0.2))
        
        return mutated

    async def _evolve_prompt_with_llm(self, current_prompt: str, feedback: Optional[str]) -> str:
        """Uses the meta-model to rewrite the prompt chromosome."""
        system_msg = SystemMessage(content=(
            "You are a Prompt Evolution Engine. Your goal is to rewrite the given 'prompt chromosome' "
            "to improve its performance in financial analysis tasks. "
            "Incorporate provided feedback if available. Maintain the core functional intent of the skill. "
            "Output ONLY the new prompt text."
        ))
        
        user_content = f"Current Prompt: {current_prompt}"
        if feedback:
            user_content += f"\nPerformance Feedback: {feedback}"
            
        response = await self.meta_model.ainvoke([system_msg, HumanMessage(content=user_content)])
        return response.content.strip()

    def crossover(self, parent1: SkillGenotype, parent2: SkillGenotype) -> List[SkillGenotype]:
        child1 = parent1.model_copy()
        child1.skill_id = f"{parent1.skill_id}_child1_{int(time.time())}"
        child1.prompt_chromosome = parent2.prompt_chromosome

        child2 = parent2.model_copy()
        child2.skill_id = f"{parent2.skill_id}_child2_{int(time.time())}"
        child2.prompt_chromosome = parent1.prompt_chromosome

        return [child1, child2]

    def select(self, population: List[SkillGenotype], count: int) -> List[SkillGenotype]:
        return sorted(population, key=lambda x: x.fitness_score, reverse=True)[:count]
