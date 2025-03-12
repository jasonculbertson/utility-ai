#!/usr/bin/env python3

import os
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class BillHandler(FileSystemEventHandler):
    def __init__(self, bills_folder):
        self.bills_folder = bills_folder
        self.processing = False
        
    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith('.pdf'):
            return
        
        print(f"New bill detected: {event.src_path}")
        self.process_bills()
        
    def process_bills(self):
        if self.processing:
            print("Already processing bills. Will process new bills when current batch completes.")
            return
            
        self.processing = True
        try:
            print("\nStarting bill processing...")
            subprocess.run(['python', 'process_bill_complete.py'], check=True)
            print("Bill processing complete!\n")
        except Exception as e:
            print(f"Error processing bills: {e}")
        finally:
            self.processing = False

def main():
    bills_folder = 'bills_to_process'
    
    # Create the folder if it doesn't exist
    if not os.path.exists(bills_folder):
        os.makedirs(bills_folder)
        print(f"Created folder: {bills_folder}")
    
    # Set up the file watcher
    event_handler = BillHandler(bills_folder)
    observer = Observer()
    observer.schedule(event_handler, bills_folder, recursive=False)
    observer.start()
    
    print(f"Monitoring {bills_folder} folder for new bills...")
    print("Press Ctrl+C to stop monitoring")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
