from crewai import Agent, Crew, Task
from crewai_tools import ScrapeWebsiteTool
from logging_config import get_logger

class ResearchCrew:
    def __init__(self, verbose=True, logger=None):
        self.verbose = verbose
        self.logger = logger or get_logger(__name__)
        self.crew = self.create_crew()
        self.logger.info("ResearchCrew initialized")

    def create_crew(self):
        self.logger.info("Creating research crew with agents")
        
        # Create scraping tool
        scrape_tool = ScrapeWebsiteTool()
        
        researcher = Agent(
            role='Research Analyst',
            goal='Find and analyze key information',
            backstory='Expert at extracting information',
            verbose=self.verbose,
            tools=[scrape_tool]
        )

        writer = Agent(
            role='Content Summarizer',
            goal='Create clear summaries from research',
            backstory='Skilled at transforming complex information',
            verbose=self.verbose
        )

        self.logger.info("Created research and writer agents")

        crew = Crew(
            agents=[researcher, writer],
            tasks=[
                Task(
                    description='Research and analyze the sentiment of tweets about $NMKR from this URL: https://pastebin.com/raw/kvA7YFQR. Identify key complaints, issues, and the overall market sentiment.',
                    expected_output='Detailed analysis of $NMKR sentiment with major issues identified',
                    agent=researcher
                ),
                Task(
                    description='Write a comprehensive summary of the $NMKR sentiment analysis. Include the main criticisms, potential red flags, and overall market perception.',
                    expected_output='Clear and concise summary of the $NMKR sentiment analysis with actionable insights',
                    agent=writer
                )
            ]
        )
        self.logger.info("Crew setup completed")
        return crew