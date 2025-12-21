from typing import Dict, Any
from src.framework.base_task import BaseTaskModule

class ConsoleNotifierTask(BaseTaskModule):
    """
    Simple notifier for testing: prints notification to stdout and returns success.
    Does not require Flask app context or DB access.
    """
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        line_user_id = inputs.get('line_user_id')
        channel_id = inputs.get('channel_id')
        final_post_title = inputs.get('final_post_title')
        hatena_entry = inputs.get('hatena_entry')
        msg_type = inputs.get('message_type', 'success')

        print(f"[ConsoleNotifier] type={msg_type} user={line_user_id} channel={channel_id} title={final_post_title}")
        if hatena_entry:
            print(f"[ConsoleNotifier] entry_url={hatena_entry.get('url')}")

        return {}

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            'name': 'ConsoleNotifier',
            'description': 'Lightweight notifier that prints to console (for tests).',
            'inputs': {'line_user_id': 'str (optional)', 'channel_id': 'str (optional)', 'final_post_title': 'str', 'hatena_entry': 'dict (optional)', 'message_type': 'str (optional)'},
            'outputs': {}
        }
