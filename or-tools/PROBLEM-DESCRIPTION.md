We need to create a work schedule for a company with 30 employees over a specified period (7 or 14 days). The company operates continuously with three shifts per day, and each employee has a specific role that determines which shifts they can work.

Employee Composition
--------------------

*   **5 Supervisors** - can work morning shifts.
    
*   **10 Mechanics** - can work any shift type.
    
*   **15 Workers** - can work morning, day, and night shifts.
    

Shift Requirements
------------------

Each day has three shifts with specific staffing needs:

*   **Morning Shift**: Requires 1 supervisor + 1 mechanic + 1 worker (3 people total)
    
*   **Day Shift**: Requires 1 mechanic + 2 workers (3 people total)
    
*   **Night Shift**: Requires 1 mechanic + 1 worker (2 people total)
    

Scheduling Constraints
----------------------

The schedule must satisfy the following rules:

*   **One shift per day**: Each employee can work at most one shift per day.
    
*   **No morning after night**: An employee cannot work a morning shift if they worked the night shift the previous day.
    
*   **Maximum consecutive days**: No employee can work more than 6 consecutive days without a day off.
    
*   **Workload balance**: The total number of shifts assigned to employees of the same role should be as balanced as possible.
    
*   **Complete coverage**: Every shift must be fully staffed according to the requirements above.
    
*   **Role restrictions**: Employees can only work shifts that match their role capabilities.