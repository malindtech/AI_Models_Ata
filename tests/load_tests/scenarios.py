"""
Day 9: Load Testing Scenarios
Pre-defined test scenarios for different load patterns
"""

# Scenario 1: Light Load (Baseline)
SCENARIO_LIGHT = {
    "name": "Light Load",
    "users": 5,
    "spawn_rate": 1,
    "duration": "5m",
    "description": "5 concurrent users, ideal for baseline metrics"
}

# Scenario 2: Normal Load (Target)
SCENARIO_NORMAL = {
    "name": "Normal Load",
    "users": 20,
    "spawn_rate": 2,
    "duration": "10m",
    "description": "20 concurrent users (10 content + 10 support), production target"
}

# Scenario 3: Peak Load
SCENARIO_PEAK = {
    "name": "Peak Load",
    "users": 40,
    "spawn_rate": 5,
    "duration": "10m",
    "description": "40 concurrent users (20 content + 20 support), stress test"
}

# Scenario 4: Spike Test
SCENARIO_SPIKE = {
    "name": "Spike Test",
    "users": 50,
    "spawn_rate": 25,  # Rapid spawn
    "duration": "5m",
    "description": "Sudden traffic spike, tests system resilience"
}

# Scenario 5: Endurance Test
SCENARIO_ENDURANCE = {
    "name": "Endurance Test",
    "users": 15,
    "spawn_rate": 1,
    "duration": "30m",
    "description": "Long-running test for memory leaks and stability"
}

# Scenario 6: Cache Effectiveness Test
SCENARIO_CACHE = {
    "name": "Cache Test",
    "users": 10,
    "spawn_rate": 5,
    "duration": "5m",
    "description": "Repeated queries to measure cache hit rate"
}

# Command templates for each scenario
def get_command(scenario: dict, host: str = "http://localhost:8000") -> str:
    """Generate Locust command for a scenario"""
    return (
        f"locust -f tests/load_tests/locustfile.py "
        f"--host {host} "
        f"--users {scenario['users']} "
        f"--spawn-rate {scenario['spawn_rate']} "
        f"--run-time {scenario['duration']} "
        f"--headless "
        f"--print-stats"
    )


def print_scenarios():
    """Print all available scenarios"""
    scenarios = [
        SCENARIO_LIGHT,
        SCENARIO_NORMAL,
        SCENARIO_PEAK,
        SCENARIO_SPIKE,
        SCENARIO_ENDURANCE,
        SCENARIO_CACHE
    ]
    
    print("\n" + "="*80)
    print("DAY 9: AVAILABLE LOAD TEST SCENARIOS")
    print("="*80 + "\n")
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario['name']}")
        print(f"   Users: {scenario['users']}, Spawn Rate: {scenario['spawn_rate']}, Duration: {scenario['duration']}")
        print(f"   {scenario['description']}")
        print(f"\n   Command:")
        print(f"   {get_command(scenario)}\n")


if __name__ == "__main__":
    print_scenarios()
