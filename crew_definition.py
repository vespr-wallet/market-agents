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
        
        # Common instruction for all agents to avoid searching the internet
        internet_restriction = "IMPORTANT: DO NOT search the internet or access any websites except the specific pastebin links provided in your tasks. Only use the exact URLs provided."
        
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

        crew = Crew(
            agents=[researcher, market_analyst, portfolio_analyst, summarizer, trade_executor],
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
                    description='Analyze the user\'s current portfolio from this data: https://pastebin.com/raw/vvSmadNF. ONLY use this exact URL - do not try to access other websites. If you encounter any errors, work with the raw data provided in the task description: The portfolio includes  Cardano (12500 ADA, $7,625.00, -2.3%), NMKR (850000 tokens, $854.25, -12.6%) with a total portfolio value of 8479.25 (-3.5%). Evaluate NMKR exposure, overall portfolio risk, and potential impact of NMKR price movements on the portfolio.',
                    expected_output='Portfolio risk assessment regarding NMKR holdings with actionable recommendations',
                    agent=portfolio_analyst,
                    async_execution=False
                ),
                Task(
                    description='Synthesize all analyses to provide a complete assessment of $NMKR and recommendations for the user. Provide specific trading recommendations for ADA/NMKR with clear buy/sell directives and target quantities.',
                    expected_output='Complete situation summary with portfolio-specific recommendations and explicit trading directives for ADA/NMKR',
                    agent=summarizer,
                    async_execution=False
                ),
                Task(
                    description='Execute the trading recommendations provided by the Financial Intelligence Summarizer. Implement these trades, considering market conditions, timing, and optimal execution strategies. Report back on execution status, actual trade prices, and any deviations from the recommendations.',
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