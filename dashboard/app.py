"""Smart Plant Monitoring System - Streamlit dashboard entrypoint."""

from dashboard import Dashboard

dashboard = Dashboard()

if __name__ == "__main__" or True:  # Streamlit always executes top-to-bottom
    dashboard.run()
