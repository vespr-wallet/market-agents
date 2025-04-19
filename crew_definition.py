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
        
        # Create scraping tools
        sentiment_scrape_tool = ScrapeWebsiteTool()
        price_scrape_tool = ScrapeWebsiteTool()
        
        researcher = Agent(
            role='Sentiment Analyst',
            goal='Analyze social media sentiment and identify key concerns',
            backstory='Expert at extracting sentiment from social media posts and identifying trends in public opinion',
            verbose=self.verbose,
            tools=[sentiment_scrape_tool]
        )

        market_analyst = Agent(
            role='Market Data Analyst',
            goal='Analyze price trends and market behavior',
            backstory='Financial analyst specialized in cryptocurrency price movements and market patterns',
            verbose=self.verbose,
            tools=[price_scrape_tool]
        )
        
        summarizer = Agent(
            role='Financial Intelligence Summarizer',
            goal='Create comprehensive analysis combining sentiment and market data',
            backstory='Expert at synthesizing multiple data sources to provide actionable intelligence for investors',
            verbose=self.verbose
        )

        self.logger.info("Created sentiment analyst, market analyst, and summarizer agents")

        crew = Crew(
            agents=[researcher, market_analyst, summarizer],
            tasks=[
                Task(
                    description='Research and analyze the sentiment of tweets about $NMKR from this URL: https://pastebin.com/raw/kvA7YFQR. Identify key complaints, issues, and the overall market sentiment.',
                    expected_output='Detailed analysis of $NMKR sentiment with major issues identified',
                    agent=researcher
                ),
                Task(
                    description='Analyze the price data for $NMKR from this URL: https://pastebin.com/f9WqwW66. Identify price trends, volatility patterns, and correlate with potential market events.',
                    expected_output='Comprehensive price analysis with identified patterns and market behavior',
                    agent=market_analyst
                ),
                Task(
                    description='Synthesize the sentiment analysis and price data to provide a complete assessment of $NMKR. Determine if negative sentiment is reflected in price action, identify potential causes, and provide an overall evaluation of the project\'s status and prospects.',
                    expected_output='Complete situation summary connecting sentiment and price action with actionable insights',
                    agent=summarizer
                )
            ]
        )
        self.logger.info("Crew setup completed")
        return crew