"""
🚀 VIAGOGO MONITOR - SIMPLE STARTER
Clean solution to run everything
"""
import subprocess
import sys
import time
from datetime import datetime

def start_backend():
    """Start FastAPI backend"""
    print("🔌 Starting backend API...")
    return subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'viagogo_dashboard.api:app', '--reload', '--port', '8000'],
        cwd='.',
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def start_frontend():
    """Start React frontend"""
    print("🎨 Starting frontend dashboard...")
    return subprocess.Popen(
        ['npm', 'run', 'dev'],
        cwd='viagogo_dashboard/client',
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def start_periodic_scraper():
    """Start periodic price scraper"""
    print("🤖 Starting periodic scraper (every 30 min)...")
    return subprocess.Popen(
        [sys.executable, 'periodic_automated.py'],
        cwd='.'
    )

def main():
    print("="*70)
    print("  🎯 VIAGOGO PRICE MONITOR - STARTING")
    print("="*70)
    print()
    
    # Start services
    backend = start_backend()
    time.sleep(3)
    
    frontend = start_frontend()
    time.sleep(3)
    
    scraper = start_periodic_scraper()
    
    print()
    print("="*70)
    print("✅ ALL SERVICES RUNNING!")
    print("="*70)
    print()
    print("📊 Dashboard:    http://localhost:5173")
    print("🔌 API:          http://localhost:8000")
    print("🤖 Scraper:      Running every 30 minutes")
    print()
    print("Press Ctrl+C to stop all services")
    print("="*70)
    print()
    
    try:
        # Keep running
        while True:
            time.sleep(60)
            # Check if services are still running
            if backend.poll() is not None:
                print("⚠ Backend stopped, restarting...")
                backend = start_backend()
            if frontend.poll() is not None:
                print("⚠ Frontend stopped, restarting...")
                frontend = start_frontend()
    except KeyboardInterrupt:
        print("\n\n⏹ Stopping all services...")
        backend.terminate()
        frontend.terminate()
        scraper.terminate()
        print("✅ All services stopped. Goodbye!")

if __name__ == '__main__':
    main()
