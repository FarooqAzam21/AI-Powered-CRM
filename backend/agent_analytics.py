import json
import pandas as pd

def load_agents():
    with open("agents.json", "r") as f:
        return json.load(f)

def agent_workload(tickets_df):
    agents = load_agents()
    data = []

    for team, agent_list in agents.items():
        for agent in agent_list:
            agent_tickets = tickets_df[tickets_df["Agent"] == agent]

            high_priority = agent_tickets[
                agent_tickets["Priority"].str.contains("High", na=False)
            ]

            count = len(agent_tickets)

            status = (
                "🟢 Low" if count < 5 else
                "🟡 Medium" if count < 10 else
                "🔴 High"
            )

            data.append({
                "Agent": agent,
                "Team": team,
                "Total Tickets": count,
                "High Priority": len(high_priority),
                "Workload": status
            })

    return pd.DataFrame(data)
