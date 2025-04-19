from crewai import Agent, Crew, Task, Process
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
        portfolio_scrape_tool = ScrapeWebsiteTool()
        
        researcher = Agent(
            role='Sentiment Analyst',
            goal='Analyze social media sentiment and identify key concerns',
            backstory='Expert at extracting sentiment from social media posts and identifying trends in public opinion',
            verbose=self.verbose,
            tools=[sentiment_scrape_tool],
            allow_delegation=True
        )

        market_analyst = Agent(
            role='Market Data Analyst',
            goal='Analyze price trends and market behavior',
            backstory='Financial analyst specialized in cryptocurrency price movements and market patterns',
            verbose=self.verbose,
            tools=[price_scrape_tool],
            allow_delegation=True
        )
        
        portfolio_analyst = Agent(
            role='Portfolio Risk Analyst',
            goal='Analyze user portfolio composition and exposure to assets',
            backstory='Specialized in evaluating investment portfolios, risk assessment, and providing recommendations for risk management',
            verbose=self.verbose,
            tools=[portfolio_scrape_tool],
            allow_delegation=True
        )
        
        summarizer = Agent(
            role='Financial Intelligence Summarizer',
            goal='Create comprehensive analysis combining sentiment, market data, and portfolio risk',
            backstory='Expert at synthesizing multiple data sources to provide actionable intelligence and recommendations for investors',
            verbose=self.verbose,
            allow_delegation=True
        )

        self.logger.info("Created sentiment analyst, market analyst, portfolio analyst, and summarizer agents")

        crew = Crew(
            agents=[researcher, market_analyst, portfolio_analyst, summarizer],
            tasks=[
                Task(
                    description='Research and analyze the sentiment of tweets about $NMKR from this URL: https://pastebin.com/raw/kvA7YFQR. ONLY use this exact URL - do not try to access other websites. If you encounter any errors, work with the raw data provided in the task description: The tweets include complaints about lack of updates, stagnation, bugs in the platform, empty promises, toxic community, plummeting market cap, and lack of transparency. Identify key complaints, issues, and the overall market sentiment.',
                    expected_output='Detailed analysis of $NMKR sentiment with major issues identified',
                    agent=researcher,
                    async_execution=False
                ),
                Task(
                    description='Analyze the price data for $NMKR from this URL: https://pastebin.com/raw/f9WqwW66. ONLY use this exact URL - do not try to access other websites. If you encounter any errors, work with the raw data provided in the task description: The data shows a consistent price decline from 0.001150 to 0.001005 over a 24-hour period. Identify price trends, volatility patterns, and correlate with potential market events.',
                    expected_output='Comprehensive price analysis with identified patterns and market behavior',
                    agent=market_analyst,
                    async_execution=False
                ),
                Task(
                    description='Analyze the user\'s current portfolio from this data: https://pastebin.com/raw/vvSmadNF. ONLY use this exact URL - do not try to access other websites. If you encounter any errors, work with the raw data provided in the task description: The portfolio includes Bitcoin (0.75 BTC, $58,425.75, +1.2%), Ethereum (8.5 ETH, $21,930.50, -0.8%), Cardano (12500 ADA, $7,625.00, -2.3%), NMKR (850000 tokens, $854.25, -12.6%), Solana (45 SOL, $6,750.00, +3.1%), USDC (5000, $5,000.00, 0.0%) with a total portfolio value of $100,585.50 (-0.5%). Evaluate NMKR exposure, overall portfolio risk, and potential impact of NMKR price movements on the portfolio.',
                    expected_output='Portfolio risk assessment regarding NMKR holdings with actionable recommendations',
                    agent=portfolio_analyst,
                    async_execution=False
                ),
                Task(
                    description='Synthesize all analyses (sentiment, price data, and portfolio risk) to provide a complete assessment of $NMKR and recommendations for the user. Ask questions to all three analysts to clarify any points. Determine if negative sentiment is reflected in price action, assess portfolio risk exposure, identify potential causes of market behavior, and provide an overall evaluation of the project\'s status with specific recommendations for the user\'s holdings.',
                    expected_output='Complete situation summary with portfolio-specific recommendations and risk management strategy',
                    agent=summarizer,
                    async_execution=False
                )
            ],
            process=Process.sequential,
            verbose=self.verbose,
            manager_llm=None  # Will use the default LLM
        )
        self.logger.info("Crew setup completed with sequential process")
        return crew