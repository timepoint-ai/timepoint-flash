#!/usr/bin/env python3
import json, os, sqlite3, sys, httpx, networkx as nx, matplotlib.pyplot as plt, logfire
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import re
from dotenv import load_dotenv

load_dotenv(Path(".env"), override=True)
logfire.configure(service_name="social-sim")

class NodeState(Enum):
    NEUTRAL = "neutral"
    ACTIVE = "active"
    RESOLVED = "resolved"

@dataclass
class SimStep:
    step: int
    interactions: list
    state_changes: list

@dataclass
class SimConfig:
    scenario: str
    nodes: int = 5
    steps: int = 3
    model: str = "meta-llama/llama-2-7b-chat"
    max_tokens: int = 1000
    temperature: float = 0.5
    timeout: int = 60

class SimulationMonolith:
    def __init__(self, config: SimConfig):
        self.config = config
        self.ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.out_dir = Path(f"outputs/{self.ts}")
        self.db_path = Path(f"data_files/sim_{self.ts}.db")
        self.graph = nx.Graph()
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.sim_data = {"steps": []}
        
    def initialize(self):
        with logfire.span("initialization"):
            logfire.info(f"Initializing simulation: {self.config.scenario}")
            
            self.out_dir.mkdir(parents=True, exist_ok=True)
            Path("data_files").mkdir(exist_ok=True)
            
            if not self.api_key:
                logfire.error("OPENROUTER_API_KEY not set")
                raise ValueError("Set OPENROUTER_API_KEY env var")
            
            self._init_db()
            self._init_graph()
            logfire.info(f"Output: {self.out_dir}")
    
    def _init_db(self):
        with logfire.span("database_init"):
            self.db = sqlite3.connect(self.db_path)
            self.db.execute("""CREATE TABLE IF NOT EXISTS sim (
                id INTEGER PRIMARY KEY,
                key TEXT,
                value TEXT,
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            self.db.commit()
            logfire.debug("Database ready")
    
    def _init_graph(self):
        with logfire.span("graph_init"):
            self.graph.add_nodes_from([
                (i, {
                    "role": f"actor_{i}",
                    "state": NodeState.NEUTRAL.value,
                    "influence": 0.5
                })
                for i in range(self.config.nodes)
            ])
            logfire.info(f"Created {len(self.graph.nodes())} nodes")
    
    def get_graph_json(self):
        return {
            "nodes": [{"id": n, **self.graph.nodes[n]} for n in self.graph.nodes()],
            "edges": [{"from": u, "to": v, "weight": self.graph[u][v].get("weight", 1)} 
                     for u, v in self.graph.edges()]
        }
    
    def run_llm_step(self):
        with logfire.span("llm_orchestration"):
            with open("prompt.json") as f:
                prompt = json.load(f)
            
            graph_json = self.get_graph_json()
            user_msg = prompt["user"].format(
                scenario=self.config.scenario,
                graph=json.dumps(graph_json),
                step_num=len(self.sim_data["steps"]) + 1
            )
            
            logfire.info(f"Calling {self.config.model}...")
            logfire.debug(f"Prompt: {len(user_msg)} chars, Graph: {len(graph_json['nodes'])} nodes")
            
            with logfire.span("api_call"):
                resp = httpx.post(
                    "https://openrouter.io/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "HTTP-Referer": "http://localhost",
                    },
                    json={
                        "model": self.config.model,
                        "messages": [
                            {"role": "system", "content": prompt["system"]},
                            {"role": "user", "content": user_msg}
                        ],
                        "max_tokens": self.config.max_tokens,
                        "temperature": self.config.temperature,
                    },
                    timeout=self.config.timeout
                ).json()
            
            try:
                content = resp["choices"][0]["message"]["content"]
                logfire.debug(f"Response: {len(content)} chars")
                self.db.execute("INSERT INTO sim (key, value) VALUES (?, ?)",
                              ("llm_step", content))
                self.db.commit()
                return content
            except (KeyError, IndexError) as e:
                logfire.error(f"API parse failed: {resp}")
                raise ValueError(f"LLM API error: {resp}")
    
    def parse_simulation_step(self, llm_response: str) -> dict:
        with logfire.span("parse_step"):
            try:
                match = re.search(r'\{[\s\S]*\}', llm_response)
                step_data = json.loads(match.group()) if match else {
                    "interactions": [],
                    "states": []
                }
                logfire.debug(f"Parsed: {len(step_data.get('interactions', []))} interactions")
                return step_data
            except Exception as e:
                logfire.warn(f"Parse fallback: {e}")
                return {"interactions": [], "states": []}
    
    def apply_simulation_step(self, step_idx: int, step_data: dict):
        with logfire.span(f"apply_step_{step_idx}"):
            interactions = step_data.get("interactions", [])
            state_changes = step_data.get("states", [])
            
            for inter in interactions:
                src, dst = inter.get("from"), inter.get("to")
                if src is not None and dst is not None and src in self.graph and dst in self.graph:
                    weight = inter.get("weight", 1)
                    self.graph.add_edge(src, dst, weight=weight)
                    logfire.debug(f"  Edge {src}->{dst} w={weight}")
            
            for state_change in state_changes:
                nid = state_change.get("id")
                if nid in self.graph:
                    new_state = state_change.get("state", NodeState.NEUTRAL.value)
                    self.graph.nodes[nid]["state"] = new_state
                    logfire.debug(f"  Node {nid} -> {new_state}")
            
            self.sim_data["steps"].append(asdict(SimStep(
                step=step_idx,
                interactions=interactions,
                state_changes=state_changes
            )))
    
    def render_frame(self, step_idx: int):
        with logfire.span(f"render_step_{step_idx}"):
            pos = nx.spring_layout(self.graph, k=1.5, iterations=50, seed=42)
            fig, ax = plt.subplots(figsize=(10, 8), dpi=80)
            
            color_map = {
                NodeState.NEUTRAL.value: "lightblue",
                NodeState.ACTIVE.value: "lightcoral",
                NodeState.RESOLVED.value: "lightgreen"
            }
            
            node_colors = [color_map.get(self.graph.nodes[n].get("state"), "gray") 
                          for n in self.graph.nodes()]
            
            nx.draw_networkx_nodes(self.graph, pos, node_color=node_colors, node_size=900, ax=ax)
            nx.draw_networkx_edges(self.graph, pos, alpha=0.3, ax=ax, width=1.5)
            
            labels = {n: f"{n}\n({self.graph.nodes[n].get('role')})" for n in self.graph.nodes()}
            nx.draw_networkx_labels(self.graph, pos, labels, font_size=8, ax=ax)
            
            ax.set_title(f"Step {step_idx}: {self.config.scenario[:50]}...", fontsize=13, fontweight="bold")
            ax.axis("off")
            
            img_path = self.out_dir / f"step_{step_idx}.png"
            plt.savefig(img_path, bbox_inches="tight", dpi=80)
            plt.close()
            logfire.info(f"Rendered: {img_path.name}")
    
    def simulate(self):
        with logfire.span("full_simulation"):
            self.initialize()
            
            for step_idx in range(self.config.steps):
                with logfire.span(f"step_{step_idx}"):
                    logfire.info(f"=== Step {step_idx + 1}/{self.config.steps} ===")
                    
                    llm_response = self.run_llm_step()
                    step_data = self.parse_simulation_step(llm_response)
                    self.apply_simulation_step(step_idx, step_data)
                    self.render_frame(step_idx)
            
            self.finalize()
    
    def finalize(self):
        with logfire.span("finalize"):
            output = {
                "scenario": self.config.scenario,
                "config": asdict(self.config),
                "initial_nodes": self.config.nodes,
                "final_nodes": len(self.graph.nodes()),
                "final_edges": len(self.graph.edges()),
                "simulation": self.sim_data
            }
            
            with open(self.out_dir / "simulation.json", "w") as f:
                json.dump(output, f, indent=2)
            
            self.db.close()
            logfire.info(f"✓ Complete: {self.out_dir}")
            logfire.info(f"  - Frames: step_0.png, step_1.png, step_2.png")
            logfire.info(f"  - Data: simulation.json")
            logfire.info(f"  - DB: {self.db_path}")

def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith("-"):
        sys.exit("Usage: python monolith.py 'scenario' [-v for verbose]")
    
    verbose = "-v" in sys.argv
    scenario = sys.argv[1]
    
    config = SimConfig(scenario=scenario)
    monolith = SimulationMonolith(config)
    
    try:
        monolith.simulate()
    except Exception as e:
        logfire.error(f"Simulation failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
