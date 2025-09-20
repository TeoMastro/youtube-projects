# -*- coding: utf-8 -*-
"""
Created on Sat Sep 20 16:48:49 2025
@author: TEO
"""
import pandas as pd
import json
from scheduling_solver import SchedulingSolver

# Read the data
with open('data.json', 'r') as file:
    data = json.load(file)
df = pd.DataFrame(data['employees'])

# Constants
DAYS = 365
SHIFTS = ['morning', 'day', 'night']
ROLES = ['supervisor', 'mechanic', 'worker']

# Create dictionaries for easier access
employees = df.to_dict('records')
employee_by_role = {role: [emp for emp in employees if emp['role'] == role] for role in ROLES}

print(f"Scheduling for {DAYS} days")
print(f"Supervisors: {len(employee_by_role['supervisor'])}")
print(f"Mechanics: {len(employee_by_role['mechanic'])}")
print(f"Workers: {len(employee_by_role['worker'])}")

# Solve the problem
print("\nSolving scheduling problem...")
scheduler = SchedulingSolver(employees, employee_by_role, DAYS, SHIFTS, ROLES)
success = scheduler.solve()

if not success:
    print("Could not find a feasible schedule with the given constraints.")
    print("You may need to:")
    print("- Increase the number of employees")
    print("- Relax some constraints")
    print("- Extend the solving time")
