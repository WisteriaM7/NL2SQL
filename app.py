import streamlit as st
import pandas as pd
import sqlite3
from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()
# Initialize DeepSeek client
client = OpenAI(
    api_key = os.getenv("API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

# Clean SQL output from AI
def clean_sql(raw_sql):
    return raw_sql.replace("```sql", "").replace("```", "").strip().lstrip("sql").strip()

# Convert NL to SQL
def generate_sql(nl_query, table_name, column_names):
    quoted_table_name = f'"{table_name}"'
    quoted_columns = [f'"{col}"' for col in column_names]
    
    prompt = f"""
Convert the following natural language request into a valid SQLite SQL query:

Table name: {quoted_table_name}
Columns: {', '.join(quoted_columns)}
Natural Language: "{nl_query}"

Only return the SQL query.
"""
    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-prover-v2:free",
            messages=[
                {"role": "system", "content": "You convert natural language into SQL queries."},
                {"role": "user", "content": prompt}
            ],
            stream=False
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

# App setup
st.set_page_config(page_title="NL2SQL - Query Tool", page_icon="📊")
st.title("📊 NL2SQL: Natural Language to SQL")

st.markdown("### 📂 Upload the CSV/Excel File")
uploaded_file = st.file_uploader("Upload your CSV or Excel file", type=["csv", "xlsx"])

df, conn, table_name, column_names = None, None, "", []

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
    st.success("✅ File uploaded successfully!")
    st.dataframe(df.iloc[:, :5])
    table_name = uploaded_file.name.split('.')[0]
    column_names = df.columns.tolist()
    conn = sqlite3.connect(":memory:")
    df.to_sql(table_name, conn, index=False, if_exists="replace")
else:
    table_name = st.text_input("Enter table name (for manual use):").strip()
    column_list_input = st.text_input("Enter column names (comma-separated):").strip()
    if table_name and column_list_input:
        column_names = [col.strip() for col in column_list_input.split(",")]
        conn = sqlite3.connect(":memory:")
        dummy_df = pd.DataFrame(columns=column_names)
        dummy_df.to_sql(table_name, conn, index=False, if_exists="replace")

st.markdown("### 💬 Enter a Natural Language Query")
nl_query = st.text_input("Enter your query:")

if st.button("🔍 Generate and Run SQL"):
    if not nl_query.strip():
        st.warning("Please enter a natural language query.")
    elif not table_name or not column_names:
        st.warning("Upload a file or enter table name and columns to proceed.")
    else:
        with st.spinner("Generating SQL query..."):
            sql_raw = generate_sql(nl_query, table_name, column_names)
            sql = clean_sql(sql_raw)
            st.code(sql, language="sql")
            try:
                conn.execute(sql)
                st.success("✅ Query executed successfully.")
            except Exception as e:
                st.error(f"Execution Error: {e}")