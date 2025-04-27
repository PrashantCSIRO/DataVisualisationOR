# streamlit_app.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Set Streamlit page configuration
st.set_page_config(page_title="Water Quality Data Visualisation", layout="wide")

# Add instructions in the sidebar
with st.sidebar:
    st.title("Instructions")

    st.markdown("""
    ### Data Formatting Requirements:
    - Upload a **CSV**, **XLS**, or **XLSX** file.
    - The file can contain **multiple sheets** (if Excel).
    - **First column**: `Pond` names (text).
    - **Second column**: `Sampling Date` (date format preferred).
    - **Subsequent columns**: Water quality parameters (numeric values).
    - **Values** with:
      - `<number` (e.g., `<0.1`) will be **converted to 0**.
      - Blank cells or `-` will also be **converted to 0**.

    ### How to Use the App:
    1. **Upload** your dataset.
    2. **Select** a sheet (if applicable).
    3. **Choose** the Pond and/or Sampling Date.
    4. **Visualise**:
       - Scatter plots between any two parameters.
       - Time series of selected parameters.
       - Ratio of two parameters over time.
    5. **Download** plots if needed (use Plotly's inbuilt export options).

    ### Additional Notes:
    - Dates on x-axis are shown monthly to avoid crowding.
    - All plots update automatically when selections change.
    - You can explore data for **all ponds** or a **single pond**.
    """)

# Upload file
uploaded_file = st.file_uploader("Upload your spreadsheet (CSV, XLS, or XLSX)", type=['csv', 'xls', 'xlsx'])

if uploaded_file:
    # Detect file type and read accordingly
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
        sheets = {'Sheet1': df}
    else:
        xls = pd.ExcelFile(uploaded_file)
        sheets = {sheet_name: pd.read_excel(uploaded_file, sheet_name=sheet_name, engine='openpyxl') for sheet_name in xls.sheet_names}

    # Select a sheet
    sheet_selected = st.selectbox("Select a sheet to work with:", list(sheets.keys()))
    df = sheets[sheet_selected]

    st.subheader("Raw Uploaded Data")
    st.dataframe(df)

    # Data Cleaning
    df.replace(to_replace=r'<\s*\d*\.?\d+', value='0', regex=True, inplace=True)  # Replace values like <0.1 with 0
    df.replace(['-', np.nan], 0, inplace=True)  # Replace blank cells or "-" with 0
    df.iloc[:, 2:] = df.iloc[:, 2:].apply(pd.to_numeric, errors='coerce').fillna(0)  # Ensure numeric columns

    # Set Indices
    df.set_index([df.columns[0], df.columns[1]], inplace=True)
    df.index.names = ['Pond', 'Sampling Date']

    # Reset index for dropdown selections
    df_reset = df.reset_index()

    # Ensure Sampling Date is properly formatted as datetime
    df_reset['Sampling Date'] = pd.to_datetime(df_reset['Sampling Date'], errors='coerce')
    df_reset = df_reset.dropna(subset=['Sampling Date'])  # Drop rows with invalid Sampling Date

    # Dropdown Selections
    ponds = df_reset['Pond'].unique()
    selected_pond = st.selectbox("Select Pond", options=np.append(["All"], ponds))

    dates = df_reset['Sampling Date'].dt.strftime('%Y-%m-%d').unique()
    selected_date = st.selectbox("Select Sampling Date", options=np.append(["All"], dates))

    # Filter Data based on Pond and Date selections
    filtered_df = df_reset.copy()
    if selected_pond != "All":
        filtered_df = filtered_df[filtered_df['Pond'] == selected_pond]
    if selected_date != "All":
        filtered_df = filtered_df[filtered_df['Sampling Date'].dt.strftime('%Y-%m-%d') == selected_date]

    # Parameters for plotting
    parameters = [col for col in df.columns if col not in ['Pond', 'Sampling Date']]
    if not parameters:
        st.error("No numeric parameters available for plotting.")
    else:
        st.markdown("---")

        # Scatter Plot
        st.subheader("Scatter Plot between Two Parameters")
        col1, col2 = st.columns(2)
        with col1:
            x_param = st.selectbox("Select X-axis Parameter", options=parameters, key="xparam")
        with col2:
            y_param = st.selectbox("Select Y-axis Parameter", options=parameters, key="yparam")

        scatter_fig = px.scatter(filtered_df, 
                                 x=x_param, 
                                 y=y_param, 
                                 color='Pond',
                                 hover_data=['Sampling Date'],
                                 labels={x_param: x_param, y_param: y_param},
                                 title=f"Scatter Plot: {x_param} vs {y_param}")

        st.plotly_chart(scatter_fig, use_container_width=True)

        st.markdown("---")

        # Time Series Plot (Parameters over Time)
        st.subheader("Time Series Line Chart of Parameters Over Time")
        selected_params_time = st.multiselect("Select Parameters to Plot Over Time", options=parameters, default=parameters[:1])

        time_df = df_reset.copy()
        if selected_pond != "All":
            time_df = time_df[time_df['Pond'] == selected_pond]

        time_series_fig = px.line(time_df, 
                                  x='Sampling Date', 
                                  y=selected_params_time,
                                  markers=True,
                                  labels={'Sampling Date': 'Sampling Date'},
                                  title="Parameter(s) Over Time")

        time_series_fig.update_layout(
            xaxis_title="Sampling Date",
            yaxis_title="Parameter Values",
            xaxis=dict(
                tickformat="%b %Y",
                tickangle=90,
                dtick="M1"  # Monthly interval
            )
        )

        st.plotly_chart(time_series_fig, use_container_width=True)

        st.markdown("---")

        # Time Series Plot (Ratios over Time)
        st.subheader("Time Series Line Chart of Parameter Ratios Over Time")
        ratio_numerator = st.selectbox("Select Numerator Parameter", options=parameters, key="numerator")
        ratio_denominator = st.selectbox("Select Denominator Parameter", options=parameters, key="denominator")

        ratio_df = time_df.copy()
        # Avoid division by zero and handle missing values
        ratio_df['Ratio'] = ratio_df[ratio_numerator] / ratio_df[ratio_denominator].replace(0, np.nan)
        ratio_df = ratio_df.dropna(subset=['Ratio'])  # Drop rows with NaN ratios

        ratio_fig = px.line(ratio_df, 
                            x='Sampling Date', 
                            y='Ratio',
                            markers=True,
                            labels={'Sampling Date': 'Sampling Date', 'Ratio': f"{ratio_numerator}/{ratio_denominator}"},
                            title=f"Ratio of {ratio_numerator} to {ratio_denominator} Over Time")

        ratio_fig.update_layout(
            xaxis_title="Sampling Date",
            yaxis_title=f"Ratio: {ratio_numerator}/{ratio_denominator}",
            xaxis=dict(
                tickformat="%b %Y",
                tickangle=90,
                dtick="M1"  # Monthly interval
            )
        )

        st.plotly_chart(ratio_fig, use_container_width=True)

else:
    st.info("Please upload a CSV, XLS, or XLSX file to proceed.")

