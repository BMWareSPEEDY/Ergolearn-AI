import os
import json
import random
from datetime import datetime, timedelta

# Standard location for application user database
HISTORY_FILE_PATH = os.path.join(os.path.expanduser("~"), ".ergolearn", "posture_history.json")

def seed():
    os.makedirs(os.path.dirname(HISTORY_FILE_PATH), exist_ok=True)
    
    now = datetime.now()
    logs = []
    
    # Generate data for the last 7 days (Monday to Sunday)
    for day_offset in range(6, -1, -1):
        target_day = now - timedelta(days=day_offset)
        
        # Skip weekends to simulate a typical work week
        if target_day.weekday() >= 5:
            continue
            
        # Session 1: 9:00 AM (Good posture, slowly decaying)
        start_time_1 = target_day.replace(hour=9, minute=0, second=0, microsecond=0)
        for i in range(200):
            # Gradual fatigue: score decays slowly from 95 to 88
            score = 95.0 - (i * 0.035) + random.uniform(-2, 2)
            score = max(0.0, min(100.0, score))
            
            # Screen distance: decays slowly from 55cm to 48cm
            dist = 55.0 - (i * 0.03) + random.uniform(-1, 1)
            dist = max(30.0, min(100.0, dist))
            
            # Brightness: stable office lighting around 200 lux
            bright = 200.0 + random.uniform(-10, 10)
            
            # Concentration: decays from 90% to 80%
            concen = 90.0 - (i * 0.04) + random.uniform(-1, 1)
            concen = max(0.0, min(100.0, concen))
            
            timestamp = start_time_1 + timedelta(seconds=i * 10)
            logs.append({
                "timestamp": timestamp.isoformat(),
                "score": round(score, 1),
                "slouching": score < 75.0,
                "fhp": False,
                "asymmetry": False,
                "screen_distance": round(dist, 1),
                "ambient_brightness": round(bright, 1),
                "concentration_index": round(concen, 1)
            })
            
        # Session 2: 2:00 PM (Decent start, but slumps heavily after 3:00 PM)
        start_time_2 = target_day.replace(hour=14, minute=0, second=0, microsecond=0)
        for i in range(200):
            timestamp = start_time_2 + timedelta(seconds=i * 10)
            
            # 3:00 PM corresponds to i >= 60 (10 mins * 6 = 60 points)
            if i < 60:
                # Good posture
                score = 91.0 - (i * 0.05) + random.uniform(-2, 2)
                score = max(0.0, min(100.0, score))
                slouching = False
                dist = 53.0 - (i * 0.05) + random.uniform(-1, 1)
                dist = max(30.0, min(100.0, dist))
                concen = 88.0 - (i * 0.05) + random.uniform(-1, 1)
                concen = max(0.0, min(100.0, concen))
            else:
                # Heavy slouching slump (drops by ~35% score)
                score = 58.0 - ((i - 60) * 0.06) + random.uniform(-3, 3)
                score = max(0.0, min(100.0, score))
                slouching = True
                dist = 44.0 - ((i - 60) * 0.04) + random.uniform(-2, 2)
                dist = max(30.0, min(100.0, dist))
                concen = 55.0 - ((i - 60) * 0.08) + random.uniform(-2, 2)
                concen = max(0.0, min(100.0, concen))
                
            bright = 190.0 + random.uniform(-15, 15)
            
            logs.append({
                "timestamp": timestamp.isoformat(),
                "score": round(score, 1),
                "slouching": slouching,
                "fhp": score < 70.0 and random.choice([True, False]),
                "asymmetry": False,
                "screen_distance": round(dist, 1),
                "ambient_brightness": round(bright, 1),
                "concentration_index": round(concen, 1)
            })

    with open(HISTORY_FILE_PATH, "w") as f:
        json.dump(logs, f, indent=2)
        
    print(f"Successfully seeded {len(logs)} fake posture log entries into {HISTORY_FILE_PATH}")

if __name__ == "__main__":
    seed()
