# ========== HOW TO RUN THIS APP ==============
#
# 1. Install required libraries:
#    pip install streamlit pandas plotly
#
# 2. Navigate to your project folder:
#    cd path_to_your_project_folder
#
# 3. Run the app:
#    python -m streamlit run main.py
#
# 4. Open in browser if needed:
#    http://localhost:8501
#
# 5. Upload a CSV file with columns:
#    Date, Details, Amount, Currency, Debit/Credit
#
# 6. Use the dashboard:
#    - Select currency (prevents mixing values)
#    - Edit categories
#    - Apply changes to train auto-categorization
#
# 7. Categories persist in:
#    categories.json
#
# 8. App Features
#    Upload multiple bank statement CSV files
#    Automatic transaction categorization using keyword matching
#    Manual category editing with learning from user changes
#    Multi-currency support for all transactions
#    Separate views for Expenses (Debits) and Payments (Credits)
#    Category-wise spending breakdown
#    Currency-wise spending breakdown
#    Interactive charts for quick financial insights
#    Payment summaries grouped by currency for clarity
#
# ==============================
