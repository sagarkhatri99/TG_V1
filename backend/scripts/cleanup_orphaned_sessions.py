import os

def cleanup_orphaned_sessions():
    """
    Deletes any orphaned .session files from the backend directory.
    """
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    for f in os.listdir(backend_dir):
        if f.endswith('.session'):
            os.remove(os.path.join(backend_dir, f))
            print(f"Removed orphaned session file: {f}")

if __name__ == "__main__":
    cleanup_orphaned_sessions()
