import pandas as pd
import json
import os

TICKETS_FILE = "tickets.csv"
AGENTS_FILE = "agents.json"

def auto_assign_agent(team):
    if not os.path.exists(AGENTS_FILE):
        return None

    with open(AGENTS_FILE, "r") as f:
        agents = json.load(f)

    team_agents = agents.get(team, [])
    if not team_agents:
        return None

    if not os.path.exists(TICKETS_FILE):
        return team_agents[0]

    df = pd.read_csv(TICKETS_FILE)

    workload = {}
    for agent in team_agents:
        workload[agent] = len(df[df["AssignedAgent"] == agent])

    # Least loaded agent
    return min(workload, key=workload.get)
