import os
import logging
from typing import Optional, Any
from dotenv import load_dotenv

logger = logging.getLogger("tark.graph.connection")

def get_tigergraph_connection(env_path: Optional[str] = None) -> Any:
    """Returns an authenticated TigerGraphConnection instance from environment variables.
    
    Returns None if pyTigerGraph is not available or required environment variables are unset.
    """
    if env_path:
        load_dotenv(env_path)
    else:
        # Default to root .env
        root_env = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
        if os.path.exists(root_env):
            load_dotenv(root_env)

    host = os.getenv("TG_HOST")
    username = os.getenv("TG_USERNAME", "tigergraph")
    password = os.getenv("TG_PASSWORD", "tigergraph")
    graphname = os.getenv("TG_GRAPHNAME", "FraudInvestigation")
    secret = os.getenv("TG_SECRET")

    if not host or not secret:
        logger.warning("TG_HOST or TG_SECRET unset in environment. Real GSQL execution unavailable.")
        return None

    try:
        import pyTigerGraph as tg
        conn = tg.TigerGraphConnection(
            host=host,
            username=username,
            password=password,
            graphname=graphname,
            gsqlSecret=secret,
            tgCloud=True
        )
        return conn
    except Exception as e:
        logger.error(f"Failed to establish TigerGraph connection: {e}")
        return None
