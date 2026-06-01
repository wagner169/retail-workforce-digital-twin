# Retail Workforce Digital Twin

A workforce scheduling and retail operations simulation platform built using Mixed Integer Linear Programming (MILP), Streamlit, Plotly, Docker, and Python.

## Project Overview

This project was developed as part of an Operations Analytics assignment focused on workforce scheduling optimization.

The system combines mathematical optimization with interactive business intelligence and digital twin visualization, allowing users to simulate staffing scenarios, operational demand changes, employee absences, and workforce allocation decisions in real time.

## Features

### Workforce Optimization

* Mixed Integer Linear Programming (MILP) model
* Employee availability constraints
* Skill matching
* Maximum working hours constraints
* Demand coverage optimization

### Interactive Dashboard

* KPI monitoring
* Fulfillment rate analysis
* Assigned hours tracking
* Unmet demand visualization
* Scenario comparison

### Retail Digital Twin

* Interactive 3D retail store visualization
* Workforce allocation simulation
* Operational heatmaps
* Employee movement tracking
* Congestion zone detection
* Time-slot simulation controls

### Scenario Analysis

* Demand multiplier simulation
* Employee absence simulation
* Workforce capacity adjustments
* Real-time optimization reruns

## Technology Stack

* Python
* Streamlit
* Plotly
* Pandas
* OR-Tools
* Docker

## Repository Structure

```text
.
├── app.py
├── solver.py
├── requirements.txt
├── Dockerfile
└── data/
    ├── employees.csv
    ├── activities.csv
    ├── demand.csv
    ├── availability.csv
    ├── skills.csv
    ├── optimized_schedule.csv
    └── unmet_demand.csv
```

## Deployment

The application has been containerized using Docker and deployed to a cloud server with a dedicated domain.

## Learning Outcomes

This project demonstrates practical applications of:

* Operations Research
* Workforce Scheduling
* Mixed Integer Programming
* Digital Twin Simulation
* Business Analytics
* Data Visualization
* Cloud Deployment
* Docker Containerization

## Author

Wagner Moreno

University of Niagara Falls Canada
