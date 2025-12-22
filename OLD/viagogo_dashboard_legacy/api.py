from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import pandas as pd
import os
import json
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "prices.db"

def get_db_connection():
    try:
        if not os.path.exists(DB_NAME):
            return None
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"DB Error: {e}")
        return None

@app.get("/matches")
def get_matches():
    try:
        # Load all games from JSON source
        if not os.path.exists("all_games_to_scrape.json"):
             return []
             
        with open("all_games_to_scrape.json", "r") as f:
            games = json.load(f)
            
        # Helper to sort by match number
        def get_match_number(match_name):
            match = re.search(r'Match (\d+)', match_name)
            return int(match.group(1)) if match else 9999

        # Format and sort
        matches_list = [{"match_name": g["match_name"], "match_url": g["url"]} for g in games]
        matches_list.sort(key=lambda x: get_match_number(x["match_name"]))
        
        return matches_list
    except Exception as e:
        print(f"Error loading matches: {e}")
        return []

@app.get("/history")
def get_history(match_url: str):
    conn = get_db_connection()
    if not conn: return {"categories": [], "data": {}}
    
    try:
        query = "SELECT * FROM price_history WHERE match_url = ? ORDER BY timestamp"
        df = pd.read_sql_query(query, conn, params=(match_url,))
        
        if df.empty:
            return {"categories": [], "data": {}}
            
        categories = df['category'].unique().tolist()
        data = {}
        for cat in categories:
            cat_df = df[df['category'] == cat]
            data[cat] = cat_df[['timestamp', 'price']].to_dict(orient='records')
            
        return {"categories": categories, "data": data, "currency": df['currency'].iloc[0] if not df.empty else "USD"}
    except Exception as e:
        print(f"Error: {e}")
        return {}
    finally:
        conn.close()
