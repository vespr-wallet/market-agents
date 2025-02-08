from crewai import Agent, Task, Crew
from typing import Optional

class CrewExecutor:
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
    
    async def execute_task(self, input_data: str) -> str:
        researcher = Agent(
            role='Research Analyst',
            goal='Find and analyze key information',
            backstory='Expert at extracting information',
            verbose=self.verbose
        )
        
        writer = Agent(
            role='Content Summarizer',
            goal='Create clear summaries from research',
            backstory='Skilled at transforming complex information',
            verbose=self.verbose
        )
        
        crew = Crew(
            agents=[researcher, writer],
            tasks=[
                Task(description=f'Research: {input_data}', agent=researcher),
                Task(description='Write summary', agent=writer)
            ]
        )
        return str(crew.kickoff()) 