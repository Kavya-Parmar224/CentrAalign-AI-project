import os
import sys
import time
import subprocess

def main():
    if not os.environ.get('GEMINI_API_KEY') and not os.path.exists('.env'):
        print("\033[93mWARNING: GEMINI_API_KEY is not set.\033[0m")
    
    os.makedirs('screenshots', exist_ok=True)
    
    print("\033[94mStarting Acme Corp Demo App on port 5001...\033[0m")
    demo_process = subprocess.Popen([sys.executable, 'demo_app/app.py'])
    
    time.sleep(2)
    
    print("\033[92mStarting API Server on port 8000...\033[0m")
    api_process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'api.server:app', '--port', '8000'])
    
    time.sleep(2)
    
    print("\n\033[1m=== Services Running ===\033[0m")
    print("Demo App:   http://localhost:5001")
    print("API Server: http://localhost:8000")
    print("Frontend:   http://localhost:3000")
    print("API Docs:   http://localhost:8000/docs")
    print("Press Ctrl+C to stop all services.\n")
    
    try:
        demo_process.wait()
        api_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        demo_process.terminate()
        api_process.terminate()
        demo_process.wait()
        api_process.wait()
        print("Done.")

if __name__ == '__main__':
    main()
