"""
Backward-compatible entry point (the original project was started with `python index.py`).
The application now lives in the `app/` package; see run.py.
"""
from run import app

if __name__ == '__main__':
    app.run()
