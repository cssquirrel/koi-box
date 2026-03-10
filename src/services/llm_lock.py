"""Shared lock for LLM model access.

Both lyrics and bio generation load the same Qwen model onto the GPU.
This lock prevents simultaneous loads that would cause OOM or corruption.
"""

import threading

llm_lock = threading.Lock()
