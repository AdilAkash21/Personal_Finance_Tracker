import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

# ---------------- APP CONFIGURATION ----------------
# Sets up basic app metadata and layout (wide layout gives more room for tables/charts)
st.set_page_config(page_title="Simple Finance App", page_icon="💰", layout="wide")

# File used to persist user-defined categories and their keywords
categories_file = "categories.json"

# ---------------- SESSION STATE INITIALIZATION ----------------
# Session state keeps data persistent across Streamlit reruns (important for UI interactions)
if "categories" not in st.session_state:
    st.session_state.categories = {
        "Uncategorized": [],  # Default fallback category
    }
    
# Load saved categories from disk (if available)
# This ensures user-defined categories persist between app runs
if os.path.exists("categories.json"):
    with open("categories.json", "r") as f:
        st.session_state.categories = json.load(f)
        
# Save current categories (with keywords) to disk
def save_categories():
    with open("categories.json", "w") as f:
        json.dump(st.session_state.categories, f)
        
# ---------------- AUTO-CATEGORIZATION LOGIC ----------------
# Assign categories based on keywords found in transaction details
def categorize_transaction(df):
    # Initialize all rows as Uncategorized
    df["Category"] = "Uncategorized"
    
    # Iterate through user-defined categories and their keyword lists
    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorized" or not keywords:
            continue  # Skip default or empty categories
        
        # Normalize keywords for case-insensitive matching
        lowered_keywords = [keyword.lower() for keyword in keywords]
        
        # Check each transaction row
        for idx, row in df.iterrows():
            details = row["Details"].lower()
            
            # NOTE: This simple keyword matching can lead to false positives (e.g., "SPINNEYS AE" matches both "Shopping" and "Gift").
            if any(keyword in details for keyword in lowered_keywords):
                df.at[idx, "Category"] = category
                break
            
    return df

# ---------------- DATA LOADING & CLEANING ----------------

def load_transactions(file):
    try:
        df = pd.read_csv(file)
        
        # Clean column names (avoids bugs from accidental spaces in CSV headers)
        df.columns = [col.strip() for col in df.columns]
        
        # Normalize currency format (e.g., "usd" -> "USD")
        df["Currency"] = df["Currency"].str.upper().str.strip()
        
        # Convert Amount to numeric safely (handles both strings and numbers)
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
        
        # Drop invalid/missing amounts to prevent calculation errors
        df = df.dropna(subset=["Amount"])
        
        # Convert Date column to datetime (required for proper sorting/filtering)
        df["Date"] = pd.to_datetime(df["Date"], format="%d %b %Y")
        
        # Apply keyword-based categorization
        return categorize_transaction(df)
    
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        return None
    
# ---------------- CATEGORY LEARNING SYSTEM ----------------

# Adds new keywords to categories based on user edits
def add_keyword_to_category(Category, keyword):
    keyword = keyword.strip()
    
    # Avoid duplicates and empty values
    if keyword and keyword not in st.session_state.categories[Category]:
        st.session_state.categories[Category].append(keyword)
        save_categories()  # Persist update
        return True
    
    return False
        
# ---------------- MAIN APP UI ----------------

def main():
    st.title("Simple Finance Dashboard")
    
    # File uploader for transaction CSV
    uploaded_file = st.file_uploader("Upload your transaction CSV file", type=["csv"])
    
    if uploaded_file is not None:
        df = load_transactions(uploaded_file)
        
        if df is not None:
            
            # Extract available currencies dynamically from dataset
            currencies = df["Currency"].unique().tolist()
            
            # User selects which currency to view
            # IMPORTANT: This prevents mixing different currencies in calculations
            selected_currency = st.selectbox("Select Currency", currencies)
            
            # Filter transactions by selected currency AND type
            debits_df = df[
                (df["Debit/Credit"] == "Debit") & 
                (df["Currency"] == selected_currency)
            ].copy()
            
            credits_df = df[
                (df["Debit/Credit"] == "Credit") & 
                (df["Currency"] == selected_currency)
            ].copy()
            
            # Store editable data in session state so edits persist across reruns
            st.session_state.debits_df = debits_df.copy()
            
            # Create two main views: Expenses and Payments
            tab1, tab2 = st.tabs(["Expenses (Debits)", "payments (Credits)"])
            
            # ---------------- TAB 1: EXPENSE MANAGEMENT ----------------
            
            with tab1:
                
                # Input field for adding new categories
                new_category = st.text_input("New Category Name")
                add_button = st.button("Add Category") 
                
                # Create category if it doesn't already exist
                if add_button and new_category:
                    if new_category not in st.session_state.categories:
                        st.session_state.categories[new_category] = []
                        save_categories()
                        st.rerun()  # Refresh UI to reflect new category
                        
                st.subheader("Your Expenses")
                
                # Editable transaction table
                # Users can manually change categories here
                edited_df = st.data_editor(
                    st.session_state.debits_df[["Date", "Details", "Amount", "Category"]],
                    column_config={
                        "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                        "Amount": st.column_config.NumberColumn(
                            "Amount", 
                            format=f"%.2f {selected_currency}"
                        ),
                        "Category": st.column_config.SelectboxColumn(
                            "Category",
                            options=list(st.session_state.categories.keys())
                        )
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="category_editor"
                )
                
                # Apply user edits
                save_button = st.button("Apply Changes", type="primary")
                
                if save_button:
                    for idx, row in edited_df.iterrows():
                        new__category = row["Category"]
                        
                        # Skip unchanged rows (performance optimization)
                        if new__category == st.session_state.debits_df.at[idx, "Category"]:
                            continue
                        
                        details = row["Details"]
                        
                        # Update category
                        st.session_state.debits_df.at[idx, "Category"] = new__category
                        
                        # Learn from user action (adds keyword for future auto-categorization)
                        add_keyword_to_category(new__category, details)
                        
                # ---------------- EXPENSE SUMMARY ----------------
                st.subheader('Expense Summary')
                
                # Aggregate total spending per category
                category_totals = (
                    st.session_state.debits_df
                    .groupby("Category")["Amount"]
                    .sum()
                    .reset_index()
                )
                
                # Sort by highest spending
                category_totals = category_totals.sort_values("Amount", ascending=False)
                
                # Display summary table
                st.dataframe(
                    category_totals,
                    column_config={
                        "Amount": st.column_config.NumberColumn(
                            "Amount", 
                            format=f"%.2f {selected_currency}"
                        )                                         
                    },            
                    use_container_width=True,
                    hide_index=True    
                )
                
            # ---------------- VISUALIZATION ----------------
            
            # Pie chart gives quick overview of spending distribution
            fig = px.pie(
                category_totals,
                names="Category",
                values="Amount",
                title="Expense Distribution by Category",
            )
            
            st.plotly_chart(fig, use_container_width=True)
                
            # ---------------- TAB 2: PAYMENTS ----------------
            
            with tab2:
                st.subheader("Payments Summary")
                
                # Total income for selected currency
                total_payments = credits_df["Amount"].sum()
                
                st.metric(
                    "Total Payments", 
                    f"{total_payments:,.2f} {selected_currency}"
                )
                
                # Raw transaction view for credits
                st.write(credits_df)
                
# Run the app
main()
