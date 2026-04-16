# 🏛️ Smart Campus Intelligence (SCI)
### Making Campus Management Easy with Data & AI

[![Live Demo](https://img.shields.io/badge/Live-Demo_Link-blue?style=for-the-badge&logo=streamlit)](https://campusanalyzer-mid-prep.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.9+-green?style=for-the-badge&logo=python)]()
[![Streamlit](https://img.shields.io/badge/Built%20With-Streamlit-red?style=for-the-badge&logo=streamlit)]()

---

## Project Overview

Managing a large campus is difficult because many things happen at the same time:

- Electricity usage
- WiFi usage
- Mess crowd
- Bus delays
- Library usage

Usually this data is stored in different places, so it is hard to understand everything together.

### Solution

Smart Campus Intelligence collects all campus data and shows it in one dashboard.

It helps administrators:

- see what is happening now
- predict future problems
- take better decisions

Result:
- saves money
- reduces problems
- improves student experience

---

## Live Demo

Open the project here:

https://campusanalyzer-mid-prep.streamlit.app/

---

## Problems Solved

| Problem | Solution |
|--------|---------|
| high electricity cost | predicts energy usage |
| slow wifi | shows network load |
| long mess queues | predicts busy time |
| bus delays | analyzes delay pattern |
| poor planning | AI gives recommendations |

---

## Features

### Electricity Analytics
- view electricity trends
- detect unusual spikes
- predict future usage
- suggest savings

example insight:
electricity usage increases during summer afternoons

---

### WiFi Analytics
- shows connected devices
- identifies peak usage time
- detects slow internet areas

---

### Mess Crowd Prediction
- predicts busy meal times
- estimates waiting time
- helps reduce queues

---

### Transport Analytics
- tracks bus delays
- shows passenger load
- suggests more buses when needed

---

### AI Strategist
AI analyzes campus data and gives suggestions.

example:
rain expected today → library crowd increases → add more shuttle trips

---


## How System Works

1. data is generated using simulation  
2. data stored in sqlite database  
3. ML models predict future values  
4. AI generates recommendations  
5. streamlit shows dashboard  

---

## Technologies Used

| Tool | Use |
|------|-----|
| Python | programming |
| Streamlit | dashboard |
| SQLite | database |
| Groq AI | recommendations |
| Pandas | data processing |
| NumPy | calculations |

---

## Run Locally

### Step 1 clone repository


git clone https://github.com/nitingargiitr/Campus_Analyzer.git

cd Campus_Analyzer


---

### Step 2 create virtual environment


-python -m venv .venv


-activate environment

on windows

.venv\Scripts\activate


on mac/linux

source .venv/bin/activate


---

### Step 3 install requirements


pip install -r requirements.txt


---

### Step 4 generate data


python scripts/run_pipeline.py


---

### Step 5 run dashboard


streamlit run apps/Dashboard.py


---

## Use Cases

### university administration
- reduce cost
- better planning
- whole campus analysis at one place


---

## Future Improvements

- real sensor data
- mobile app
- alert system
- real time user data analysis

---

## Author

Nitin Garg and Pranav Garg

If you like the project give it a star on github.
