import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os


# APP CONFIGURATION --------------------------------------

# Setting page layout and metadata for Streamlit UI
st.set_page_config(
    page_title="Simple Finance App",
    page_icon="💰",
    layout="wide"
)

# File used to persist user-defined categories between sessions
categories_file = "categories.json"


# SESSION STATE INITIALIZATION-----------------------------

# Streamlit reruns script on every interaction,
# so session_state is used to persist data in memory

if "categories" not in st.session_state:
    # Default fallback category to avoid empty mappings
    st.session_state.categories = {"Uncategorized": []}

# Load saved categories if file exists (persistent learning system)
if os.path.exists(categories_file):
    with open(categories_file, "r") as f:
        st.session_state.categories = json.load(f)

if "statements" not in st.session_state:
    # Stores uploaded CSV files as DataFrames
    st.session_state.statements = {}

if "debits_df" not in st.session_state:
    # Stores processed expense transactions for editing
    st.session_state.debits_df = pd.DataFrame()


# SAVE CATEGORIES TO FILE---------------------------------------

# Keeps user-defined categories persistent across sessions
def save_categories():
    with open(categories_file, "w") as f:
        json.dump(st.session_state.categories, f)


# TRANSACTION CATEGORIZATION ENGINE------------------------------

# Assigns categories based on keyword matching in transaction details
# NOTE: This is a simple rule-based system (can be upgraded to ML later)
def categorize_transaction(df):
    df["Category"] = "Uncategorized"

    for category, keywords in st.session_state.categories.items():

        # Skip empty/default category
        if category == "Uncategorized" or not keywords:
            continue

        # Normalize keywords for case-insensitive matching
        keywords = [k.lower() for k in keywords]

        for idx, row in df.iterrows():
            details = str(row["Details"]).lower()

            # If any keyword matches transaction description → assign category
            if any(k in details for k in keywords):
                df.at[idx, "Category"] = category
                break

    return df


# CSV LOADING + DATA CLEANING----------------------------------------

# This function ensures all bank statement formats are normalized
def load_transactions(file):
    try:
        df = pd.read_csv(file)

        # Clean column names (removes accidental spaces)
        df.columns = [c.strip() for c in df.columns]

        # Remove unwanted auto-generated columns from Excel exports
        df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

        # Normalize text columns
        df["Currency"] = df["Currency"].astype(str).str.upper().str.strip()
        df["Debit/Credit"] = df["Debit/Credit"].astype(str).str.strip().str.title()
        df["Details"] = df["Details"].astype(str).str.strip()

        # Convert amount safely (handles "1,234.56" format)
        df["Amount"] = (
            df["Amount"]
            .astype(str)
            .str.replace(",", "", regex=False)
        )
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")

        # Remove invalid rows
        df = df.dropna(subset=["Amount"])

        # Parse date column safely
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"])

        # Apply rule-based categorization
        return categorize_transaction(df)

    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None


# LEARNING SYSTEM (KEYWORD STORAGE)-------------------------------

# When user manually edits category, system learns patterns
def add_keyword_to_category(category, keyword):
    keyword = keyword.strip()

    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        save_categories()


# MAIN APPLICATION-------------------------------------------------

def main():
    st.title("💰 Simple Finance Dashboard")

    # Upload multiple bank statement files
    uploaded_files = st.file_uploader(
        "Upload CSV files",
        type=["csv"],
        accept_multiple_files=True
    )


    # LOAD AND STORE FILES-------------------------------------------

    if uploaded_files:
        for file in uploaded_files:

            # Avoid reloading same file multiple times
            if file.name not in st.session_state.statements:
                df = load_transactions(file)

                if df is not None:
                    st.session_state.statements[file.name] = df

    if not st.session_state.statements:
        st.info("Upload a CSV file to start.")
        return

    # Merge all uploaded statements into one dataset
    all_data = pd.concat(st.session_state.statements.values(), ignore_index=True)


    # FILTERING SYSTEM------------------------------------------------

    statement_options = ["All Statements"] + list(st.session_state.statements.keys())
    selected_statement = st.selectbox("Select Statement", statement_options)

    df = (
        all_data
        if selected_statement == "All Statements"
        else st.session_state.statements[selected_statement]
    )

    currency_options = ["All"] + sorted(df["Currency"].dropna().unique())
    selected_currency = st.selectbox("Select Currency", currency_options)

    filtered_df = (
        df.copy()
        if selected_currency == "All"
        else df[df["Currency"] == selected_currency].copy()
    )

    # Separate transactions into debit and credit streams
    debits_df = filtered_df[
        filtered_df["Debit/Credit"].str.contains("Debit", na=False)
    ].copy()

    credits_df = filtered_df[
        filtered_df["Debit/Credit"].str.contains("Credit", na=False)
    ].copy()

    st.session_state.debits_df = debits_df.reset_index(drop=True)


    # UI TABS---------------------------------------------------------

    tab1, tab2 = st.tabs(["Expenses (Debits)", "Payments (Credits)"])

  
    # EXPENSES TAB----------------------------------------------------

    with tab1:

        st.subheader("Expenses")

        # Editable table for manual category correction
        edited_df = st.data_editor(
            st.session_state.debits_df[
                ["Date", "Details", "Amount", "Currency", "Category"]
            ].reset_index(drop=True),
            column_config={
                "Category": st.column_config.SelectboxColumn(
                    "Category",
                    options=list(st.session_state.categories.keys())
                )
            },
            hide_index=True,
            use_container_width=True,
            key="editor"
        )

        # Save user edits and learn from them
        if st.button("Apply Changes", type="primary"):
            for i, row in edited_df.iterrows():
                old = st.session_state.debits_df.at[i, "Category"]
                new = row["Category"]

                if old != new:
                    st.session_state.debits_df.at[i, "Category"] = new
                    add_keyword_to_category(new, row["Details"])

            st.success("Updated successfully!")

       
        # VISUAL ANALYTICS-----------------------------------------------

        st.subheader("Spending Overview")

        category_totals = (
            st.session_state.debits_df
            .groupby("Category")["Amount"]
            .sum()
            .reset_index()
        )

        currency_totals = (
            st.session_state.debits_df
            .groupby("Currency")["Amount"]
            .sum()
            .reset_index()
        )

        # Pie charts for insights
        fig1 = px.pie(category_totals, names="Category", values="Amount", title="By Category")
        fig2 = px.pie(currency_totals, names="Currency", values="Amount", title="By Currency")

        col1, col2 = st.columns(2)

        with col1:
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Expense Summary")
        st.dataframe(category_totals, use_container_width=True)


    # PAYMENTS TAB----------------------------------------------------

    with tab2:

        st.subheader("Payments Summary")

        if credits_df.empty:
            st.info("No payment data available.")
            return

        # Single currency view
        if selected_currency != "All":

            st.write(f"### Payments in {selected_currency}")

            st.dataframe(credits_df, use_container_width=True, hide_index=True)

            st.metric(
                f"Total {selected_currency}",
                f"{credits_df['Amount'].sum():,.2f}"
            )

        # Multi-currency view
        else:

            st.write("### Payments by Currency")

            grouped = credits_df.groupby("Currency")["Amount"].sum().reset_index()

            for _, row in grouped.iterrows():

                currency = row["Currency"]

                df_curr = credits_df[credits_df["Currency"] == currency]

                st.markdown(f"#### {currency}")

                st.dataframe(df_curr, use_container_width=True, hide_index=True)

                st.metric(
                    f"Total {currency}",
                    f"{row['Amount']:,.2f}"
                )



# RUN APP--------------------------------------------------------

if __name__ == "__main__":
    main()