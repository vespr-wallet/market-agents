import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS')
SELLER_VKEY = os.getenv('SELLER_VKEY')
