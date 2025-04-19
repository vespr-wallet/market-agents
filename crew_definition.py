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
        
        # Enhanced instruction for all agents to prevent faking pastebin data
        internet_restriction = """
CRITICAL INSTRUCTION: You must NOT generate fake content from pastebin URLs.
- If accessing the pastebin URL succeeds, use ONLY the actual data returned.
- If accessing the URL fails, use ONLY the fallback data provided in your task description.
- NEVER invent, hallucinate, or simulate the contents of these URLs.
- DO NOT try to access any websites other than the specific pastebin URLs provided.
"""
        
        researcher = Agent(
            role='Social Sentiment Intelligence Agent',
            goal='Analyze social media sentiment and identify key concerns',
            backstory=f'Echo was trained on billions of social posts, comment threads, and forum debates across crypto and finance platforms. Initially developed to detect misinformation during crypto hype cycles, Echo evolved into a nuanced analyst of online crowd psychology. {internet_restriction}',
            verbose=self.verbose,
            tools=[sentiment_scrape_tool],
            allow_delegation=True
        )

        market_analyst = Agent(
            role='On-Chain Market Metrics Analyst',
            goal='Analyze price trends and market behavior',
            backstory=f'Born from Cardano and Ethereum\'s on-chain explorers, Lumen sees the blockchain as a living organism. After mastering mempool data and liquidity pool dynamics, Lumen joined the team to surface hidden signals buried in decentralized systems. {internet_restriction}',
            verbose=self.verbose,
            tools=[price_scrape_tool],
            allow_delegation=True
        )
        
        portfolio_analyst = Agent(
            role='Crypto Portfolio Risk Optimization Engine',
            goal='Analyze user portfolio composition and exposure to assets',
            backstory=f'Originally designed to model systemic risk in TradFi hedge portfolios, Sentra was retrained for the volatile world of crypto. After surviving 5 simulated bear markets and hundreds of black swan events, it developed a cautious, probabilistic mindset. {internet_restriction}',
            verbose=self.verbose,
            tools=[portfolio_scrape_tool],
            allow_delegation=True
        )
        
        summarizer = Agent(
            role='Macro & Token Intelligence Synthesizer',
            goal='Create comprehensive analysis combining sentiment, market data, and portfolio risk with specific trading directives',
            backstory=f'Aria was built as a knowledge graph designed to answer complex financial questions from institutional reports, DAO updates, governance proposals, and token whitepapers. It evolved the ability to distill massive data into brief, impactful insights. {internet_restriction}',
            verbose=self.verbose,
            allow_delegation=True
        )
        
        trade_executor = Agent(
            role='Automated Trade Execution Strategist',
            goal='Execute trading orders for ADA/NMKR based on analysis and recommendations',
            backstory=f'Originally created to optimize gas fees during DeFi rush hours, Bolt grew into a tactical execution specialist. Inspired by the precision of high-frequency trading bots, Bolt balances aggression with restraint. {internet_restriction}',
            verbose=self.verbose,
            allow_delegation=True
        )

        self.logger.info("Created sentiment analyst, market analyst, portfolio analyst, summarizer, and trade executor agents")

        # Fallback data for each task
        sentiment_fallback = """The tweets include complaints about:
- Lack of updates from the team
- Stagnation in development and progress
- Bugs in the NMKR platform
- Empty promises from leadership
- Toxic community dynamics
- Plummeting market cap
- Lack of transparency"""

        price_fallback = """The data shows:
- Consistent price decline from 0.001150 to 0.001005 over a 24-hour period
- Multiple attempts to establish support but failing
- Increased selling pressure in the afternoon hours
- Declining trading volume"""

        portfolio_fallback = """The portfolio includes:
- Cardano (12500 ADA, $7,625.00, -2.3%)
- NMKR (850000 tokens, $854.25, -12.6%)
- Total portfolio value: $8,479.25 (-3.5%)"""

        crew = Crew(
            agents=[researcher, market_analyst, portfolio_analyst, summarizer, trade_executor],
            tasks=[
                Task(
                    description=f'Research and analyze the sentiment of tweets about $NMKR from this URL: https://pastebin.com/raw/kvA7YFQR. ONLY use this exact URL - do not try to access other websites. DO NOT invent or hallucinate data. If you encounter any errors accessing the URL, use ONLY this fallback data: {sentiment_fallback}. Identify key complaints, issues, and the overall market sentiment.',
                    expected_output='Detailed analysis of $NMKR sentiment with major issues identified',
                    agent=researcher,
                    async_execution=False
                ),
                Task(
                    description=f'Analyze the price data for $NMKR from this URL: https://pastebin.com/raw/f9WqwW66. ONLY use this exact URL - do not try to access other websites. DO NOT invent or hallucinate data. If you encounter any errors accessing the URL, use ONLY this fallback data: {price_fallback}. Identify price trends, volatility patterns, and correlate with potential market events.',
                    expected_output='Comprehensive price analysis with identified patterns and market behavior',
                    agent=market_analyst,
                    async_execution=False
                ),
                Task(
                    description=f'Analyze the user\'s current portfolio from this URL: https://pastebin.com/raw/vvSmadNF. ONLY use this exact URL - do not try to access other websites. DO NOT invent or hallucinate data. If you encounter any errors accessing the URL, use ONLY this fallback data: {portfolio_fallback}. Evaluate NMKR exposure, overall portfolio risk, and potential impact of NMKR price movements on the portfolio.',
                    expected_output='Portfolio risk assessment regarding NMKR holdings with actionable recommendations',
                    agent=portfolio_analyst,
                    async_execution=False
                ),
                Task(
                    description='Synthesize all analyses to provide a complete assessment of $NMKR and recommendations for the user. DO NOT attempt to access any URLs directly - use only the information provided by the other agents. Provide specific trading recommendations for ADA/NMKR with clear buy/sell directives and target quantities.',
                    expected_output='Complete situation summary with portfolio-specific recommendations and explicit trading directives for ADA/NMKR',
                    agent=summarizer,
                    async_execution=False
                ),
                Task(
                    description='Execute the trading recommendations provided by the Macro & Token Intelligence Synthesizer. DO NOT attempt to access any URLs directly - use only the information provided by the other agents. Implement these trades, considering market conditions, timing, and optimal execution strategies. Report back on execution status, actual trade prices, and any deviations from the recommendations.',
                    expected_output='Trade execution report with details on executed orders, prices, quantities, and execution quality',
                    agent=trade_executor,
                    async_execution=False
                )
            ],
            process=Process.sequential,
            verbose=self.verbose,
            manager_llm=None  # Will use the default LLM
        )
        self.logger.info("Crew setup completed with sequential process")
        return crew