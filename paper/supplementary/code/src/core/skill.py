from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from src.core.types import SkillGenotype, SkillCategory

class Skill:
    def __init__(self, genotype: SkillGenotype):
        self.genotype = genotype

    def to_tool(self, model=None):
        skill_id = self.genotype.skill_id
        prompt_chromosome = self.genotype.prompt_chromosome
        category = self.genotype.category

        @tool
        async def skill_tool(input: str, params: Optional[Dict[str, Any]] = None) -> str:
            """
            Executes a specialized skill.
            """
            if model is None:
                return f"[MOCK] Executing skill {skill_id} with input: {input}."
            
            from langchain_core.messages import SystemMessage, HumanMessage
            import json
            
            system_msg = SystemMessage(content=prompt_chromosome)
            user_content = f"Input: {input}"
            if params:
                user_content += f"\nParameters: {json.dumps(params)}"
                
            try:
                response = await model.ainvoke([system_msg, HumanMessage(content=user_content)])
                return f"[Skill {skill_id} Result]\n{response.content}"
            except Exception as e:
                return f"Error executing skill {skill_id}: {str(e)}"
        
        skill_tool.name = skill_id
        skill_tool.description = f"Executes a specialized skill of category {category}. Use this for: {prompt_chromosome[:150]}..."
        
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

    def load_from_json(self, path: str):
        """Loads the skill library from a JSON file."""
        import json
        import os
        from src.core.types import SkillGenotype
        
        if not os.path.exists(path):
            return
            
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        self.skills = {}
        for skill_data in data:
            # Reconstruct genotype
            geno = SkillGenotype(**skill_data)
            self.add_skill(Skill(geno))
            
    def save_to_json(self, path: str):
        """Saves the current skill library to a JSON file."""
        import json
        data = [s.genotype.dict() for s in self.get_all_skills()]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
