import random
import time
from typing import List
from src.core.types import SkillGenotype

class EvolutionEngine:
    def mutate(self, skill: SkillGenotype) -> SkillGenotype:
        mutation_type = random.random()
        mutated = skill.model_copy()
        mutated.skill_id = f"{skill.skill_id}_mutated_{int(time.time())}"

        if mutation_type < 0.6:
            mutated.prompt_chromosome = f"[Mutated] {skill.prompt_chromosome}"
        elif mutation_type < 0.9:
            mutated.llm_config.temperature = min(1.0, max(0.0, skill.llm_config.temperature + (random.random() - 0.5) * 0.2))
        else:
            # Structure mutation placeholder
            pass
        
        return mutated

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
