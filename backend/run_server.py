"""
Minimal FastAPI Server Starter
Avoids uvicorn import issues by using simple ASGI runner
"""
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Start the FastAPI app"""
    try:
        print("🔧 Attempting to start FastAPI app...")
        from main import app
        
        print("✅ FastAPI app imported successfully")
        print("🚀 Starting server with Daphne ASGI server...")
        
        # Try Daphne first (Django's ASGI server)
        try:
            import daphne.cli
            sys.argv = ["daphne", "-b", "127.0.0.1", "-p", "8000", "main:app"]
            daphne.cli.CommandLineInterface().run()
        except ImportError:
            print("⚠️  Daphne not available, trying Hypercorn...")
            
            # Try Hypercorn
            try:
                import hypercorn.asyncio
                import hypercorn.config
                import asyncio
                
                config = hypercorn.config.Config(
                    app="main:app",
                    bind="127.0.0.1:8000"
                )
                asyncio.run(hypercorn.asyncio.serve(config))
            except ImportError:
                print("⚠️  Hypercorn not available, trying Uvicorn directly...")
                
                # Try Uvicorn directly (simple import)
                try:
                    import uvicorn
                    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
                except Exception as e:
                    print(f"❌ Error with Uvicorn: {e}")
                    print("\n⚠️  All ASGI servers failed. Please install one:")
                    print("   pip install daphne")
                    print("   or")
                    print("   pip install hypercorn")
                    sys.exit(1)
                    
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
