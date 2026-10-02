"""
Entry point for the QuantumBit BHR Trading Bot.
Starts the FastAPI server and Uvicorn runtime.
"""

import uvicorn
from config.settings import settings
from core.database import init_db

if __name__ == "__main__":
    init_db()
    uvicorn.run(
        "api.app:app", 
        host=settings.HOST, 
        port=settings.PORT, 
        reload=False,
        log_level="info"
    )
