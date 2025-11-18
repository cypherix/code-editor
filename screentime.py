#!/usr/bin/env python3
"""
Screen Time Tracker - A minimalist time tracking application

Dependencies:
pip install tkinter (usually comes with Python)
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional

class Session:
    def __init__(self, start: str, end: Optional[str] = None):
        self.start = start
        self.end = end
    
    def to_dict(self):
        return {"start": self.start, "end": self.end}
    
    @staticmethod
    def from_dict(data):
        return Session(data["start"], data.get("end"))

class DayRecord:
    def __init__(self, date: str):
        self.date = date
        self.total_seconds = 0
        self.sessions: List[Session] = []
    
    def to_dict(self):
        return {
            "date": self.date,
            "total_seconds": self.total_seconds,
            "sessions": [s.to_dict() for s in self.sessions]
        }
    
    @staticmethod
    def from_dict(data):
        record = DayRecord(data["date"])
        record.total_seconds = data["total_seconds"]
        record.sessions = [Session.from_dict(s) for s in data["sessions"]]
        return record

class TrackerData:
    def __init__(self):
        self.records: Dict[str, DayRecord] = {}
        self.data_path = self._get_data_path()
        self.load()
    
    def _get_data_path(self) -> Path:
        """Get the path to store data"""
        if os.name == 'nt':  # Windows
            base = Path(os.environ.get('LOCALAPPDATA', Path.home()))
        else:  # macOS/Linux
            base = Path.home() / '.local' / 'share'
        
        data_dir = base / 'screen_time_tracker'
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / 'data.json'
    
    def load(self):
        """Load data from disk"""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)
                    self.records = {
                        k: DayRecord.from_dict(v) 
                        for k, v in data.get("records", {}).items()
                    }
            except Exception as e:
                print(f"Error loading data: {e}")
                self.records = {}
    
    def save(self):
        """Save data to disk"""
        try:
            data = {
                "records": {k: v.to_dict() for k, v in self.records.items()}
            }
            with open(self.data_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def start_session(self):
        """Start a new tracking session"""
        now = datetime.now()
        date_key = now.strftime("%Y-%m-%d")
        
        if date_key not in self.records:
            self.records[date_key] = DayRecord(date_key)
        
        session = Session(now.isoformat())
        self.records[date_key].sessions.append(session)
    
    def end_session(self):
        """End the current tracking session"""
        now = datetime.now()
        date_key = now.strftime("%Y-%m-%d")
        
        if date_key in self.records and self.records[date_key].sessions:
            session = self.records[date_key].sessions[-1]
            if session.end is None:
                session.end = now.isoformat()
                
                # Calculate duration
                start_time = datetime.fromisoformat(session.start)
                duration = (now - start_time).total_seconds()
                self.records[date_key].total_seconds += int(duration)
    
    def get_today_seconds(self) -> int:
        """Get total seconds tracked today"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.records.get(today, DayRecord(today)).total_seconds
    
    def get_active_session_seconds(self) -> int:
        """Get seconds for currently active session"""
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.records:
            return 0
        
        sessions = self.records[today].sessions
        if not sessions:
            return 0
        
        last_session = sessions[-1]
        if last_session.end is None:
            start_time = datetime.fromisoformat(last_session.start)
            return int((datetime.now() - start_time).total_seconds())
        
        return 0
    
    def get_month_seconds(self, year: int, month: int) -> int:
        """Get total seconds for a specific month"""
        total = 0
        for record in self.records.values():
            try:
                date = datetime.strptime(record.date, "%Y-%m-%d")
                if date.year == year and date.month == month:
                    total += record.total_seconds
            except ValueError:
                continue
        return total
    
    def get_recent_days(self, limit: int = 10) -> List[DayRecord]:
        """Get most recent days sorted by date"""
        sorted_records = sorted(
            self.records.values(), 
            key=lambda r: r.date, 
            reverse=True
        )
        return sorted_records[:limit]

class ScreenTimeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📊 Screen Time Tracker")
        self.root.geometry("450x550")
        self.root.resizable(True, True)
        
        self.data = TrackerData()
        self.is_tracking = False
        
        self._setup_ui()
        self._update_display()
    
    def _setup_ui(self):
        """Setup the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # Title
        title = ttk.Label(main_frame, text="📊 Screen Time Tracker", 
                         font=("Arial", 18, "bold"))
        title.grid(row=0, column=0, pady=(0, 20))
        
        # Today's stats
        self.today_label = ttk.Label(main_frame, text="Today: 0h 0m 0s", 
                                     font=("Arial", 14))
        self.today_label.grid(row=1, column=0, pady=5)
        
        # Month's stats
        self.month_label = ttk.Label(main_frame, text="This Month: 0h 0m", 
                                     font=("Arial", 12))
        self.month_label.grid(row=2, column=0, pady=5)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="⏸ Not Tracking", 
                                      font=("Arial", 10), foreground="gray")
        self.status_label.grid(row=3, column=0, pady=(10, 20))
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, pady=10)
        
        self.track_button = ttk.Button(button_frame, text="▶ Start Tracking", 
                                       command=self.toggle_tracking)
        self.track_button.grid(row=0, column=0, padx=5)
        
        save_button = ttk.Button(button_frame, text="💾 Save", 
                                command=self.save_data)
        save_button.grid(row=0, column=1, padx=5)
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=5, column=0, sticky=(tk.W, tk.E), pady=20
        )
        
        # Recent days label
        recent_label = ttk.Label(main_frame, text="📅 Recent Days:", 
                                font=("Arial", 11, "bold"))
        recent_label.grid(row=6, column=0, pady=(0, 10), sticky=tk.W)
        
        # Scrollable frame for recent days
        scroll_frame = ttk.Frame(main_frame)
        scroll_frame.grid(row=7, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.rowconfigure(7, weight=1)
        
        scrollbar = ttk.Scrollbar(scroll_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.days_text = tk.Text(scroll_frame, height=10, width=40, 
                                 yscrollcommand=scrollbar.set,
                                 font=("Courier", 10), 
                                 state='disabled')
        self.days_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.days_text.yview)
    
    def toggle_tracking(self):
        """Toggle tracking on/off"""
        if self.is_tracking:
            self.data.end_session()
            self.data.save()
            self.is_tracking = False
            self.track_button.config(text="▶ Start Tracking")
            self.status_label.config(text="⏸ Not Tracking", foreground="gray")
        else:
            self.data.start_session()
            self.is_tracking = True
            self.track_button.config(text="⏸ Stop Tracking")
            self.status_label.config(text="▶ Tracking...", foreground="green")
        
        self._update_display()
    
    def save_data(self):
        """Save data to disk"""
        self.data.save()
        self.status_label.config(text="✓ Saved!", foreground="blue")
        self.root.after(2000, lambda: self.status_label.config(
            text="⏸ Not Tracking" if not self.is_tracking else "▶ Tracking...",
            foreground="gray" if not self.is_tracking else "green"
        ))
    
    def _format_time(self, seconds: int) -> tuple:
        """Convert seconds to hours, minutes, seconds"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return hours, minutes, secs
    
    def _update_display(self):
        """Update all display elements"""
        # Update today's time
        today_secs = self.data.get_today_seconds()
        if self.is_tracking:
            today_secs += self.data.get_active_session_seconds()
        
        h, m, s = self._format_time(today_secs)
        self.today_label.config(text=f"Today: {h}h {m}m {s}s")
        
        # Update month's time
        now = datetime.now()
        month_secs = self.data.get_month_seconds(now.year, now.month)
        h, m, _ = self._format_time(month_secs)
        self.month_label.config(text=f"This Month: {h}h {m}m")
        
        # Update recent days list
        self.days_text.config(state='normal')
        self.days_text.delete(1.0, tk.END)
        
        for day in self.data.get_recent_days():
            h, m, _ = self._format_time(day.total_seconds)
            self.days_text.insert(tk.END, f"{day.date}: {h}h {m}m\n")
        
        self.days_text.config(state='disabled')
        
        # Schedule next update
        self.root.after(1000, self._update_display)
    
    def on_closing(self):
        """Handle window closing"""
        if self.is_tracking:
            self.data.end_session()
        self.data.save()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = ScreenTimeApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()