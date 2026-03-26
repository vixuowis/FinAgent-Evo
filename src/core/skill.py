from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from src.core.types import SkillGenotype, SkillCategory

class Skill:
    def __init__(self, genotype: SkillGenotype):
        self.genotype = genotype

    def to_tool(self):
        skill_id = self.genotype.skill_id
        prompt_chromosome = self.genotype.prompt_chromosome
        category = self.genotype.category

        @tool
        def skill_tool(input: str, params: Optional[Dict[str, Any]] = None) -> str:
            """
            Executes a specialized skill.
            """
            return f"Executing skill {skill_id} with input: {input}. Prompt context: {prompt_chromosome[:50]}..."
        
        skill_tool.name = skill_id
        skill_tool.description = f"Executes a specialized skill of category {category}. Description: {prompt_chromosome[:100]}..."
        
        return skill_tool

    def update_fitness(self, score: float):
        self.genotype.fitness_score = (self.genotype.fitness_score + score) / 2

class SkillLibrary:
    def __init__(self):
        self.skills: Dict[str, Skill] = {}

    def add_skill(self, skill: Skill):
        self.skills[skill.genotype.skill_id] = skill

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        return self.skills.get(skill_id)

    def get_all_skills(self) -> List[Skill]:
        return list(self.skills.values())

    def get_skills_by_category(self, category: SkillCategory) -> List[Skill]:
        return [s for s in self.get_all_skills() if s.genotype.category == category]
