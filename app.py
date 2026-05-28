"""
Entry point for the RAG Threads application.
Run this file to start the development server.
"""
import os
from app import create_app

# Create the Flask application
app = create_app()

if __name__ == '__main__':
    # Get host and port from environment or use defaults
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Run the development server
    app.run(host=host, port=port, debug=debug)
