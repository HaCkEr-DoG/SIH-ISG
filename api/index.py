import sys, os

# Add backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'isg', 'backend'))

# SQLite lives in /tmp on Vercel (persists per function instance, fine for demo)
os.environ.setdefault('DATABASE_URL', 'sqlite:////tmp/isg_demo.db')
os.environ.setdefault('DEMO_API_KEY', 'isg-demo-token-sih2026')
os.environ.setdefault('ALLOWED_ORIGINS', '*')
os.environ.setdefault('ENVIRONMENT', 'demo')

from main import app  # noqa: F401, E402  (app is the ASGI entry point)
