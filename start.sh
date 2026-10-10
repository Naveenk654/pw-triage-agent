#!/bin/bash
# Start the background listener
python -m src.gmail_listener &

# Start the Streamlit dashboard on the port provided by Railway
streamlit run admin_app.py --server.port $PORT --server.address 0.0.0.0
