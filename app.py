import json
import mysql.connector
import re
import google.generativeai as genai
import streamlit as st
import pandas as pd  

def load_config():
    with open("config.json", "r") as file:
        return json.load(file)

config = load_config()
API_KEY = config.get("API_KEY") 

class Custom_GenAI:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name="gemini-2.0-flash")

    def ask_ai(self, question):
        try:
            contents=f"""
            You are a helpful assistant converting natural language to SQL.
            The database is MySQL, don't use PostgreSQL or sqlite

            Convert this natural language query into SQL: {question}
            """
            response = self.model.generate_content(contents)
            return response.text 
        except Exception as e:
            st.error(f"Gemini API error: {e}")
            return None

gen_ai = Custom_GenAI(API_KEY)

DB_CONFIG = {
    "host": "localhost",
    "user": "",
    "password": "",
    "database": "Flights"  
}
st.title("CHATDB: From Natural Language to SQL")

DATABASES = ["Flights", "library_management", "Instacart"]  
selected_db = st.selectbox("Select Database", DATABASES)
DB_CONFIG["database"] = selected_db  

def connect_to_db():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

def get_schema_info():
    conn = connect_to_db()
    if not conn:
        return ""

    cursor = conn.cursor()
    try:
        cursor.execute("SHOW TABLES;")
        tables = cursor.fetchall()
        schema = ""
        for table in tables:
            table_name = table[0]
            schema += f"\nTable: {table_name}\nColumns: "
            cursor.execute(f"SHOW COLUMNS FROM {table_name};")
            columns = cursor.fetchall()
            schema += ", ".join([col[0] for col in columns]) + "\n"
        return schema
    except Exception as e:
        st.error(f"Error getting schema: {e}")
        return ""
    finally:
        cursor.close()
        conn.close()

def execute_query(sql_query):
    conn = connect_to_db()
    if not conn:
        return None  
    
    try:
        cursor = conn.cursor()
        cursor.execute(sql_query)

        if sql_query.strip().lower().startswith("select"):
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            df = pd.DataFrame(rows, columns=columns)
            return df  
        else:
            conn.commit()
            st.success("Query executed successfully.")
            return None
    except Exception as e:
        st.error(f"SQL Execution Error: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


schema_context = get_schema_info()

user_input = st.text_area("Enter your natural language query:")
if user_input:
    query_with_schema = f"{user_input}\n\nSchema:\n{schema_context}"
    sql_query = gen_ai.ask_ai(query_with_schema)

    if sql_query:
        sql_query = re.sub(r'```sql|```', '', sql_query)
        st.subheader("Generated SQL:")
        st.code(sql_query)

        if st.button("Execute SQL Query"):
            result_df = execute_query(sql_query)
            try:
                if result_df is not None:
                    st.subheader("Query Results:")
                    st.dataframe(result_df)  
            
            except Exception:
                st.error(f'try another prompt')
