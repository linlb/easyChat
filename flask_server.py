import threading
import json
import time
from flask import Flask, request, jsonify
from ui_auto_wechat import WeChat


class WeChatFlaskServer:
    def __init__(self, wechat_instance, port=6001):
        self.wechat = wechat_instance
        self.port = port
        self.app = Flask(__name__)
        self.server_thread = None
        self.is_running = False
        
        # Configure Flask routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask API routes"""
        
        @self.app.route('/', methods=['GET'])
        def index():
            """Root endpoint with API documentation"""
            return jsonify({
                "service": "EasyChat Flask API",
                "version": "1.0.0",
                "endpoints": {
                    "/": "GET - This documentation",
                    "/status": "GET - Service status",
                    "/send": "POST - Send message to WeChat contact",
                    "/health": "GET - Health check"
                },
                "usage": {
                    "/send": {
                        "method": "POST",
                        "content_type": "application/json",
                        "parameters": {
                            "recipient": "string - WeChat contact name (required)",
                            "message": "string - message content (required)",
                            "at": "array - list of people to @ (optional)"
                        },
                        "example": {
                            "recipient": "张三",
                            "message": "你好，这是一条测试消息",
                            "at": ["李四"]
                        }
                    }
                }
            })

        @self.app.route('/status', methods=['GET'])
        def status():
            """Service status endpoint"""
            return jsonify({
                "status": "running",
                "port": self.port,
                "wechat_connected": self.wechat is not None,
                "service": "EasyChat Flask API"
            })

        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            return jsonify({
                "status": "healthy",
                "timestamp": time.time()
            })

        @self.app.route('/send', methods=['POST'])
        def send_message():
            """Send message to WeChat contact"""
            try:
                data = request.get_json()
                
                if not data:
                    return jsonify({"error": "Invalid JSON format"}), 400
                
                recipient = data.get('recipient')
                message = data.get('message')
                at_list = data.get('at', [])
                
                if not recipient or not message:
                    return jsonify({
                        "error": "Missing required parameters",
                        "required": ["recipient", "message"],
                        "provided": list(data.keys())
                    }), 400
                
                # Send message using WeChat automation
                try:
                    self.wechat.send_msg(recipient, at_list, message)
                    
                    return jsonify({
                        "success": True,
                        "recipient": recipient,
                        "message": message,
                        "at": at_list,
                        "timestamp": time.time()
                    })
                    
                except Exception as e:
                    return jsonify({
                        "error": "Failed to send message",
                        "details": str(e),
                        "recipient": recipient
                    }), 500
                    
            except Exception as e:
                return jsonify({
                    "error": "Internal server error",
                    "details": str(e)
                }), 500

        @self.app.route('/contacts', methods=['GET'])
        def get_contacts():
            """Get list of all contacts"""
            try:
                contacts = self.wechat.find_all_contacts()
                return jsonify({
                    "contacts": contacts.to_dict('records') if hasattr(contacts, 'to_dict') else list(contacts),
                    "count": len(contacts)
                })
            except Exception as e:
                return jsonify({
                    "error": "Failed to get contacts",
                    "details": str(e)
                }), 500

        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({"error": "Endpoint not found", "available_endpoints": ["/", "/status", "/send", "/health", "/contacts"]}), 404

        @self.app.errorhandler(500)
        def internal_error(error):
            return jsonify({"error": "Internal server error"}), 500

    def start(self):
        """Start the Flask server in a separate thread"""
        try:
            if not self.is_running:
                self.server_thread = threading.Thread(
                    target=self.app.run,
                    kwargs={'host': '0.0.0.0', 'port': self.port, 'debug': False, 'use_reloader': False},
                    daemon=True
                )
                self.server_thread.start()
                self.is_running = True
                return True
        except Exception as e:
            print(f"Failed to start Flask server: {e}")
            return False
        return False

    def stop(self):
        """Stop the Flask server"""
        if self.is_running:
            # Note: Flask's development server doesn't have a clean shutdown method
            # In production, use a proper WSGI server like gunicorn
            self.is_running = False
            return True
        return False

    def get_status(self):
        """Get server status"""
        return {
            "running": self.is_running,
            "port": self.port,
            "url": f"http://localhost:{self.port}"
        }