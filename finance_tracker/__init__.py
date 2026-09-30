"""Personal Finance Tracker — DATA 333 (Bellevue College).

Package layout:
    models       Transaction, SavingsGoal and Budget dataclasses.
    exceptions   Custom exception hierarchy.
    storage      JSON and CSV persistence with corrupted-file recovery.
    tracker      FinanceTracker: the in-memory store and its operations.
    analytics    pandas-based summaries and trends.
    visualize    matplotlib charts saved as PNG files.
    alerts       Budget alerts and savings-goal milestones.
    cli          Interactive console menu.
    gui_tkinter  Tkinter desktop interface.
    dashboard    Streamlit interactive dashboard.
"""

__version__ = "1.0.0"
