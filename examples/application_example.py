"""Example script demonstrating the use of the application service and client.

This script shows how to start an application server and connect to it using the
application client. It demonstrates various operations like executing Python code,
importing modules, and calling functions.
"""

# Import built-in modules
import logging
import os
import sys
import threading
import time

# Add the parent directory to sys.path to allow imports without installation
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import local modules
try:
    from dcc_mcp_rpyc.application import start_application_server
    from dcc_mcp_rpyc.application import connect_to_application
except ImportError:
    # This allows the example to be run without installing the package
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def start_server_thread(app_name: str = "example_app", port: int = 18812):
    """Start the application server in a separate thread.

    Args:
    ----
        app_name: Name of the application (default: "example_app")
        port: Port to listen on (default: 18812)

    Returns:
    -------
        The server thread

    """
    # Create a thread to run the server
    server_thread = threading.Thread(
        target=start_application_server,
        args=(app_name, "1.0.0", port),
        daemon=True,
    )
    server_thread.start()
    logger.info(f"Started {app_name} server thread on port {port}")
    return server_thread


def run_client_operations(host: str = "localhost", port: int = 18812):
    """Run various client operations against the server.

    Args:
    ----
        host: Hostname or IP address of the server (default: "localhost")
        port: Port number of the server (default: 18812)

    """
    # Connect to the server
    client = connect_to_application(host, port, app_name="example_app")
    logger.info("Connected to application server")

    try:
        # Get application info
        app_info = client.get_application_info()
        logger.info(f"Application info: {app_info}")

        # Get environment info
        env_info = client.get_environment_info()
        logger.info(f"Environment info: {env_info}")

        # Execute Python code
        code = """
        import os
        import platform
        
        result = {
            'os': os.name,
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'current_dir': os.getcwd(),
        }
        """
        result = client.execute_python(code)
        logger.info(f"Python code execution result: {result}")

        # Import a module and call a function
        result = client.call_function("math", "sqrt", 16)
        logger.info(f"Math.sqrt(16) result: {result}")

        # Execute more complex code with context
        code = """
        result = {
            'input_value': input_value,
            'calculated': input_value * 2,
            'message': message
        }
        """
        context = {"input_value": 42, "message": "Hello from client!"}
        result = client.execute_python(code, context)
        logger.info(f"Python code with context result: {result}")

        # Get available actions
        actions = client.get_actions()
        logger.info(f"Available actions: {actions}")

    finally:
        # Disconnect from the server
        client.disconnect()
        logger.info("Disconnected from application server")


def main():
    """Main function to run the example."""
    # Define the port for the server
    port = 18812

    # Start the server in a separate thread
    server_thread = start_server_thread(port=port)

    # Wait for the server to start
    time.sleep(2)

    # Run client operations
    run_client_operations(port=port)

    # Keep the main thread alive for a while
    logger.info("Example completed. Press Ctrl+C to exit.")
    try:
        while server_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Exiting...")


if __name__ == "__main__":
    main()
