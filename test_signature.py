#!/usr/bin/env python3
import inspect
from src.routes_webhook import _process_user_batch_entry

sig = inspect.signature(_process_user_batch_entry)
params = list(sig.parameters.keys())
print(f"Function parameters: {params}")
print(f"Expected: ['user_id', 'messages', 'channel_id']")
print(f"Match: {params == ['user_id', 'messages', 'channel_id']}")
