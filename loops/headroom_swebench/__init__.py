"""Headroom SWE-bench — does compression break agent behavior on real tasks?

The core question: if we compress context with headroom, does the agent
make more mistakes? More tool calls? Get stuck in loops?

This loop runs SWE-bench-style tasks through headroom proxy with and
without compression, then compares: task completion, token usage, tool
calls, and time to solve.
"""
