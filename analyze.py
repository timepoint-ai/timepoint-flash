#!/usr/bin/env python3
"""Analyze simulation outputs and generate reports."""
import json
import sys
from pathlib import Path
from collections import defaultdict

def analyze_simulation(output_dir):
    """Analyze a simulation output directory."""
    output_dir = Path(output_dir)
    sim_file = output_dir / "simulation.json"
    
    if not sim_file.exists():
        print(f"❌ No simulation.json found in {output_dir}")
        return
    
    with open(sim_file) as f:
        data = json.load(f)
    
    print(f"\n📊 Simulation Report: {data['scenario']}")
    print("=" * 60)
    print(f"Initial nodes: {data['initial_nodes']}")
    print(f"Final nodes: {data['final_nodes']}")
    print(f"Final edges: {data['final_edges']}")
    print(f"Steps: {len(data['simulation'].get('steps', []))}")
    print()
    
    # Analyze interactions
    all_interactions = []
    node_activity = defaultdict(int)
    edge_types = defaultdict(int)
    
    for step in data['simulation'].get('steps', []):
        for inter in step.get('interactions', []):
            all_interactions.append(inter)
            node_activity[inter.get('from')] += 1
            node_activity[inter.get('to')] += 1
            edge_types[inter.get('type', 'unknown')] += 1
    
    print("📈 Interaction Analysis:")
    print(f"  Total interactions: {len(all_interactions)}")
    print(f"  Edge types: {dict(edge_types)}")
    print()
    
    print("🎯 Node Activity (interactions per node):")
    for node_id, count in sorted(node_activity.items(), key=lambda x: -x[1]):
        print(f"  Node {node_id}: {count} interactions")
    print()
    
    # State transitions
    state_changes = defaultdict(int)
    for step in data['simulation'].get('steps', []):
        for change in step.get('state_changes', []):
            state_changes[change.get('state', 'unknown')] += 1
    
    if state_changes:
        print("🔄 State Transitions:")
        for state, count in sorted(state_changes.items(), key=lambda x: -x[1]):
            print(f"  {state}: {count} nodes")
        print()
    
    print(f"✓ Full data saved to: {sim_file}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze_simulation(sys.argv[1])
    else:
        # Find latest output
        outputs = sorted(Path("outputs").glob("*/"))
        if outputs:
            print(f"Analyzing latest: {outputs[-1]}")
            analyze_simulation(outputs[-1])
        else:
            print("No outputs found. Run: python monolith.py 'scenario'")
