"""
Webhook Trigger - Handles HTTP webhook requests to initiate workflows.

This trigger registers Flask routes dynamically based on workflow configuration
and executes workflows when webhook requests are received.
"""

import base64
import hashlib
import hmac
import json
import logging
from typing import Any, Dict, Optional

from flask import Blueprint, request, jsonify

from src.services.framework.base_trigger import BaseTrigger

logger = logging.getLogger(__name__)


class WebhookTrigger(BaseTrigger):
    """
    Trigger that listens for HTTP webhook requests.

    Supports various authentication methods including HMAC signature verification.
    """

    def __init__(self, workflow_name: str, config: Dict[str, Any]):
        super().__init__(workflow_name, config)
        self.blueprint: Optional[Blueprint] = None
        self.app: Optional[Any] = None

    def register(self, app: Any = None) -> None:
        """
        Registers the webhook endpoint with the Flask application.

        Args:
            app (Any): Flask application instance
        """
        if not app:
            raise RuntimeError(
                f"Flask app required for WebhookTrigger (workflow: {self.workflow_name})"
            )

        self.app = app

        # Get configuration
        url_prefix = self.config.get('url_prefix', '/api/webhook')
        endpoint = self.config.get('endpoint', f'/{self.workflow_name}')
        method = self.config.get('method', 'POST')

        # Create unique blueprint name
        blueprint_name = f"webhook_{self.workflow_name}"
        self.blueprint = Blueprint(blueprint_name, __name__)

        # Create route handler
        def webhook_handler():
            return self._handle_webhook_request()

        # Register route
        self.blueprint.add_url_rule(
            endpoint,
            f'{blueprint_name}_handler',
            webhook_handler,
            methods=[method]
        )

        # Register blueprint with app
        app.register_blueprint(self.blueprint, url_prefix=url_prefix)
        logger.info(
            f"📍 Registered webhook: {method} {url_prefix}{endpoint} "
            f"-> workflow '{self.workflow_name}'"
        )

    def unregister(self) -> None:
        """
        Unregisters the webhook endpoint.

        Note: Flask doesn't natively support blueprint removal, so this is a no-op.
        """
        logger.info(f"Unregistered webhook for workflow: {self.workflow_name}")

    def _handle_webhook_request(self):
        """
        Handles incoming webhook requests.

        Returns:
            Flask response: JSON response indicating success or failure
        """
        logger.info(f"🌐 Webhook request received for workflow: {self.workflow_name}")

        # Get request data
        body = request.get_data(as_text=True)
        signature = request.headers.get('X-Line-Signature')  # Default to LINE signature header

        # Verify signature if auth is configured
        auth_config = self.config.get('auth', {})
        if auth_config.get('type') == 'hmac_signature':
            secret = auth_config.get('secret')
            signature_header = auth_config.get('header', 'X-Line-Signature')
            signature = request.headers.get(signature_header)

            if not secret:
                logger.error("HMAC secret not configured")
                return jsonify({"error": "authentication configuration error"}), 500

            if not self._verify_signature(body, signature, secret):
                logger.warning("Signature verification failed")
                return jsonify({"error": "signature verification failed"}), 403

        # Parse request body
        try:
            if request.is_json:
                payload = request.get_json()
            else:
                payload = json.loads(body) if body else {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in request: {e}")
            return jsonify({"error": "invalid json"}), 400

        # Extract initial inputs from payload
        # This can be customized based on the webhook source
        initial_inputs = self._extract_initial_inputs(payload)

        # Fire workflow
        try:
            self.fire(initial_inputs)
            return jsonify({
                "status": "ok",
                "workflow": self.workflow_name,
                "message": "Workflow triggered successfully"
            }), 200
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            return jsonify({
                "status": "error",
                "workflow": self.workflow_name,
                "error": str(e)
            }), 500

    def _verify_signature(self, body: str, signature: Optional[str], secret: str) -> bool:
        """
        Verifies HMAC signature.

        Args:
            body (str): Request body
            signature (Optional[str]): Signature from header
            secret (str): Secret key for HMAC

        Returns:
            bool: True if signature is valid
        """
        if not signature:
            return False

        mac = hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
        expected = base64.b64encode(mac).decode()
        return hmac.compare_digest(expected, signature)

    def _extract_initial_inputs(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts initial inputs from webhook payload.

        This method can be overridden or configured for different webhook sources.

        Args:
            payload (Dict[str, Any]): Webhook payload

        Returns:
            Dict[str, Any]: Initial inputs for workflow
        """
        # Default: pass entire payload
        # For LINE webhooks, you might want to extract specific fields
        source = self.config.get('source', 'generic')

        if source == 'line':
            # LINE-specific extraction logic
            # This would be handled by the existing LINE webhook handler
            # For now, return the payload as-is
            return payload

        # Generic webhook: return entire payload
        return payload

    @classmethod
    def get_trigger_info(cls) -> Dict[str, Any]:
        """
        Returns metadata about the WebhookTrigger.

        Returns:
            Dict[str, Any]: Trigger metadata
        """
        return {
            'name': 'WebhookTrigger',
            'type': 'webhook',
            'description': 'Triggers workflow execution via HTTP webhook requests',
            'config_schema': {
                'url_prefix': {
                    'type': 'string',
                    'default': '/api/webhook',
                    'description': 'URL prefix for the webhook endpoint'
                },
                'endpoint': {
                    'type': 'string',
                    'required': True,
                    'description': 'Endpoint path (e.g., /line)'
                },
                'method': {
                    'type': 'string',
                    'default': 'POST',
                    'enum': ['GET', 'POST', 'PUT', 'DELETE'],
                    'description': 'HTTP method'
                },
                'source': {
                    'type': 'string',
                    'default': 'generic',
                    'description': 'Webhook source (e.g., line, github, slack)'
                },
                'auth': {
                    'type': 'object',
                    'properties': {
                        'type': {
                            'type': 'string',
                            'enum': ['none', 'hmac_signature'],
                            'description': 'Authentication method'
                        },
                        'secret': {
                            'type': 'string',
                            'description': 'Secret key for HMAC verification'
                        },
                        'header': {
                            'type': 'string',
                            'default': 'X-Line-Signature',
                            'description': 'Header name containing signature'
                        }
                    }
                }
            }
        }
