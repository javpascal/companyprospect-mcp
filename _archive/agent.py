OPENAI_API_KEY = 'sk-placeholder'

import sys, asyncio
from agents import Agent, Runner

# Fuerza el event loop “selector” puro de Python en macOS (evita impls nativas raras)
if sys.platform == "darwin":
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

agent = Agent(name="Assistant", instructions="You are a helpful assistant.")
res = Runner.run_sync(agent, "Write a haiku about recursion in programming.")
print(res.final_output)
