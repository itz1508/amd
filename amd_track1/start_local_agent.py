#!/usr/bin/env python3
"""
Start Local Agent Wrapper

Starts llama-server for local Qwen model inference, then runs the AMD Track 1 agent.
This is the entrypoint for the local-qwen Docker image.
"""

import os
import subprocess
import sys
import time
import signal


def main():
    """Start llama server and run the agent."""
    # Find model path
    model_path = os.environ.get('LOCAL_MODEL_PATH')
    if not model_path:
        raise RuntimeError('LOCAL_MODEL_PATH not set')
    server_binary = os.environ.get('LOCAL_SERVER_BINARY')
    host = os.environ.get('LOCAL_SERVER_HOST')
    port = os.environ.get('LOCAL_SERVER_PORT')
    if not server_binary or not host or not port:
        raise RuntimeError('LOCAL_SERVER_BINARY, LOCAL_SERVER_HOST, and LOCAL_SERVER_PORT are required')
    
    # Check if model exists
    if not os.path.exists(model_path):
        print(f"Warning: Model file not found at {model_path}", file=sys.stderr)
        print("Running in Fireworks-only mode", file=sys.stderr)
        # Run agent directly without local model
        subprocess.run([sys.executable, "-m", "amd_track1.entrypoint"])
        return
    
    # Start llama server
    server_proc = None
    try:
        cmd = [
            server_binary,
            "-m", model_path,
            "--host", host,
            "--port", port,
            "-c", "4096",
            "--no-webui",
        ]
        
        print(f"Starting llama-server with model: {model_path}", file=sys.stderr)
        server_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        
        # Wait for server to start
        time.sleep(3)  # Give it a moment to initialize
        
        # Check if server is running
        if server_proc.poll() is not None:
            print(f"Server failed to start: exit code {server_proc.returncode}", file=sys.stderr)
            # Check stderr
            import select
            if server_proc.stderr:
                ready, _, _ = select.select([server_proc.stderr], [], [], 0.1)
                if ready:
                    stderr_output = server_proc.stderr.read().decode()
                    print(f"Server error: {stderr_output[:500]}", file=sys.stderr)
            subprocess.run([sys.executable, "-m", "amd_track1.entrypoint"])
            return
        
        print("Llama server started successfully", file=sys.stderr)
        
        # Wait for server port to be available
        import urllib.request
        for i in range(30):  # Wait up to 30 seconds
            try:
                urllib.request.urlopen(f"http://{host}:{port}/v1/models", timeout=1)
                print("Server is responding", file=sys.stderr)
                break
            except:
                time.sleep(1)
        else:
            print("Warning: Server may not be responding yet", file=sys.stderr)
        
        # Set environment for agent
        os.environ.setdefault('LOCAL_MODEL_URL', f'http://{host}:{port}')
        
        # Run the agent
        agent_proc = subprocess.run(
            [sys.executable, "-m", "amd_track1.entrypoint"],
        )
        
        # Pass through exit code
        sys.exit(agent_proc.returncode)
        
    finally:
        # Clean up server
        if server_proc is not None:
            print("Stopping llama-server...", file=sys.stderr)
            server_proc.terminate()
            try:
                server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_proc.kill()


if __name__ == "__main__":
    main()
