from dotenv import load_dotenv
import os

load_dotenv()

POSTGRES_USER=os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD=os.getenv("POSTGRES_PASSWORD")
SECRET_KEY=os.getenv("SECRET_KEY")
SERVER_GOOGLE_API_KEY=os.getenv("SERVER_GOOGLE_API_KEY")
EMAIL_USER=os.getenv("EMAIL_USER")
EMAIL_PASSWORD=os.getenv("EMAIL_PASSWORD")
TIMEZONE=os.getenv("TIMEZONE")

PROD = False
if "ENV" in os.environ:
    PROD = os.environ["ENV"] != "dev"

if PROD:
    BROWSER_GOOGLE_API_KEY=os.getenv("PROD_BROWSER_GOOGLE_API_KEY")
else:
    BROWSER_GOOGLE_API_KEY=os.getenv("BROWSER_GOOGLE_API_KEY")
