# -*- coding: utf-8 -*-
"""
Created on Sat Sep 20 17:10:20 2025
@author: TEO
"""
from ortools.sat.python import cp_model
from collections import defaultdict
import pandas as pd

class SchedulingSolver:
    def __init__(self, employees, employee_by_role, days, shifts, roles):
        self.model = cp_model.CpModel()
        self.employees = employees
        self.employee_by_role = employee_by_role
        self.DAYS = days
        self.SHIFTS = shifts
        self.ROLES = roles
        self.shifts = {}
        self.create_variables()
        self.add_constraints()
        
    def create_variables(self):
        """Create decision variables for each employee, day, and shift"""
        for emp in self.employees:
            for day in range(self.DAYS):
                for shift in self.SHIFTS:
                    self.shifts[(emp['id'], day, shift)] = self.model.NewBoolVar(
                        f"emp_{emp['id']}_day_{day}_shift_{shift}"
                    )
    
    def add_constraints(self):
        """Add all scheduling constraints"""
        self.add_shift_requirements()
        self.add_one_shift_per_day()
        self.add_no_morning_after_night()
        self.add_max_consecutive_days()
        self.add_workload_balance()
    
    def add_shift_requirements(self):
        """Ensure each shift has the required number of people per role"""
        for day in range(self.DAYS):
            # Morning shift: 1 supervisor, 1 mechanic, 1 worker
            self.model.Add(sum(self.shifts[(emp['id'], day, 'morning')] 
                              for emp in self.employee_by_role['supervisor']) == 1)
            self.model.Add(sum(self.shifts[(emp['id'], day, 'morning')] 
                              for emp in self.employee_by_role['mechanic']) == 1)
            self.model.Add(sum(self.shifts[(emp['id'], day, 'morning')] 
                              for emp in self.employee_by_role['worker']) == 1)
            
            # Day shift: 1 mechanic, 2 workers
            self.model.Add(sum(self.shifts[(emp['id'], day, 'day')] 
                              for emp in self.employee_by_role['mechanic']) == 1)
            self.model.Add(sum(self.shifts[(emp['id'], day, 'day')] 
                              for emp in self.employee_by_role['worker']) == 2)
            
            # Night shift: 1 mechanic, 1 worker
            self.model.Add(sum(self.shifts[(emp['id'], day, 'night')] 
                              for emp in self.employee_by_role['mechanic']) == 1)
            self.model.Add(sum(self.shifts[(emp['id'], day, 'night')] 
                              for emp in self.employee_by_role['worker']) == 1)
    
    def add_one_shift_per_day(self):
        """Each person can work at most one shift per day"""
        for emp in self.employees:
            for day in range(self.DAYS):
                self.model.Add(sum(self.shifts[(emp['id'], day, shift)] 
                                 for shift in self.SHIFTS) <= 1)
    
    def add_no_morning_after_night(self):
        """No morning shift if worked night shift the previous day"""
        for emp in self.employees:
            for day in range(1, self.DAYS):
                self.model.Add(self.shifts[(emp['id'], day-1, 'night')] + 
                             self.shifts[(emp['id'], day, 'morning')] <= 1)
    
    def add_max_consecutive_days(self):
        """No more than 6 consecutive working days"""
        for emp in self.employees:
            for start_day in range(self.DAYS - 6):
                # For each 7-day window, ensure at least 1 day off
                working_days = []
                for day in range(start_day, start_day + 7):
                    day_working = self.model.NewBoolVar(f"emp_{emp['id']}_working_day_{day}")
                    self.model.Add(sum(self.shifts[(emp['id'], day, shift)] 
                                     for shift in self.SHIFTS) >= day_working)
                    self.model.Add(sum(self.shifts[(emp['id'], day, shift)] 
                                     for shift in self.SHIFTS) <= day_working * 3)
                    working_days.append(day_working)
                
                self.model.Add(sum(working_days) <= 6)
    
    def add_workload_balance(self):
        """Try to balance workload among employees of the same role"""
        for role in self.ROLES:
            role_employees = self.employee_by_role[role]
            if len(role_employees) <= 1:
                continue
                
            # Calculate total shifts for each employee in this role
            employee_totals = []
            for emp in role_employees:
                total_shifts = sum(self.shifts[(emp['id'], day, shift)] 
                                 for day in range(self.DAYS) for shift in self.SHIFTS)
                employee_totals.append(total_shifts)
            
            # Add constraints to keep workloads balanced (within 2 shifts of each other)
            for i in range(len(employee_totals)):
                for j in range(i + 1, len(employee_totals)):
                    diff = self.model.NewIntVar(-2, 2, f"diff_{role}_{i}_{j}")
                    self.model.Add(employee_totals[i] - employee_totals[j] == diff)
    
    def solve(self):
        """Solve the scheduling problem"""
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 120
        
        status = solver.Solve(self.model)
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            print(f"Solution found! Status: {solver.StatusName(status)}")
            self.export_to_csv(solver)
            return True
        else:
            print(f"No solution found. Status: {solver.StatusName(status)}")
            return False
    
    def export_to_csv(self, solver):
        """Export solution to CSV files"""
        # Create schedule data for CSV
        schedule_data = []
        employee_stats = defaultdict(int)
        
        days_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for day in range(self.DAYS):
            day_name = days_names[day % 7]
            week_number = (day // 7) + 1
            
            for shift in self.SHIFTS:
                # Get people assigned to this shift
                supervisors = []
                mechanics = []
                workers = []
                
                for emp in self.employees:
                    if solver.Value(self.shifts[(emp['id'], day, shift)]):
                        employee_stats[emp['fullName']] += 1
                        
                        if emp['role'] == 'supervisor':
                            supervisors.append(emp['fullName'])
                        elif emp['role'] == 'mechanic':
                            mechanics.append(emp['fullName'])
                        elif emp['role'] == 'worker':
                            workers.append(emp['fullName'])
                
                # Add row to schedule data
                schedule_data.append({
                    'Day_Number': day + 1,
                    'Day_Name': day_name,
                    'Week_Number': week_number,
                    'Shift': shift.upper(),
                    'Supervisors': ', '.join(supervisors) if supervisors else '',
                    'Mechanics': ', '.join(mechanics) if mechanics else '',
                    'Workers': ', '.join(workers) if workers else ''
                })
        
        # Create schedule DataFrame and save to CSV
        schedule_df = pd.DataFrame(schedule_data)
        schedule_filename = f"schedule_{self.DAYS}_days.csv"
        schedule_df.to_csv(schedule_filename, index=False)
        print(f"Schedule saved to: {schedule_filename}")
        
        # Create workload distribution data
        workload_data = []
        role_stats = defaultdict(list)
        
        for emp in self.employees:
            role_stats[emp['role']].append((emp['fullName'], employee_stats[emp['fullName']]))
        
        for role in self.ROLES:
            role_employees = sorted(role_stats[role], key=lambda x: x[1], reverse=True)
            shift_counts = [shifts for _, shifts in role_employees]
            
            if shift_counts:
                avg_shifts = sum(shift_counts) / len(shift_counts)
                min_shifts = min(shift_counts)
                max_shifts = max(shift_counts)
                
                for name, shifts in role_employees:
                    workload_data.append({
                        'Role': role.upper(),
                        'Employee_Name': name,
                        'Total_Shifts': shifts,
                        'Role_Average': round(avg_shifts, 1),
                        'Role_Min': min_shifts,
                        'Role_Max': max_shifts,
                        'Role_Range': f"{min_shifts} - {max_shifts}"
                    })
        
        # Create workload DataFrame and save to CSV
        workload_df = pd.DataFrame(workload_data)
        workload_filename = f"workload_distribution_{self.DAYS}_days.csv"
        workload_df.to_csv(workload_filename, index=False)
        print(f"Workload distribution saved to: {workload_filename}")
        
        # Print summary to terminal
        print(f"\nFiles created:")
        print(f"  - {schedule_filename} ({len(schedule_df)} rows)")
        print(f"  - {workload_filename} ({len(workload_df)} rows)")
