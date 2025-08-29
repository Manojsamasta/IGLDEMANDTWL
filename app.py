# app.py
import streamlit as st
import pandas as pd
import numpy as np
import io

# ----------------------------
# 🎨 Streamlit Page Config
# ----------------------------
st.set_page_config(
    page_title="IGL & TW DEMAND Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"  # Right sidebar
)

# ----------------------------
# 🌑 Dark Theme Styling
# ----------------------------
st.markdown(
    """
    <style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    .stButton>button, .stDownloadButton>button { background-color: #1f2937; color: #e0e0e0; }
    .stTextInput>div>input, .stDateInput>div>input { background-color: #1f2937; color: #e0e0e0; }
    .css-1d391kg { flex-direction: row-reverse; } /* Right sidebar */
    </style>
    """, unsafe_allow_html=True
)

st.title("📊 IGL & TW Demand Dashboard")

# ----------------------------
# 📂 File Upload in Right Sidebar
# ----------------------------
with st.sidebar:
    st.header("Upload Files & Select Date")
    daily_file = st.file_uploader("Daily Collection CSV", type=['csv','tsv'])
    branch_file = st.file_uploader("Branch Excel", type=['xlsx'])
    mobile_file = st.file_uploader("Mobile CSV", type=['csv'])
    manual_date = st.date_input("Select Demand Date")

# ----------------------------
# 📝 Preview Uploaded Files
# ----------------------------
st.subheader("Uploaded File Preview")

def preview_file(file, file_type):
    if file:
        try:
            file.seek(0)
            if file_type == 'daily':
                # Force comma separator
                df = pd.read_csv(file, sep=',', encoding='ISO-8859-1', low_memory=False)
            elif file_type == 'branch':
                df = pd.read_excel(file)
            else:  # mobile
                df = pd.read_csv(file, encoding='ISO-8859-1', low_memory=False)

            df.columns = df.columns.str.strip()
            st.dataframe(df.head())
            return df
        except Exception as e:
            st.error(f"Error reading {file.name}: {e}")
            return None
    return None

Daily_Clollection_preview = preview_file(daily_file, 'daily')
branch_preview = preview_file(branch_file, 'branch')
mobile_preview = preview_file(mobile_file, 'mobile')

# ----------------------------
# ⚙️ Data Processing
# ----------------------------
if daily_file and branch_file and mobile_file:

    # Reset file pointers
    daily_file.seek(0)
    branch_file.seek(0)
    mobile_file.seek(0)

    # Read Daily Collection (force sep=',')
    Daily_Clollection = pd.read_csv(daily_file, sep=',', encoding='ISO-8859-1', low_memory=False)
    Daily_Clollection.columns = Daily_Clollection.columns.str.strip()

    # Required columns check
    required_cols = ['ClientID','BranchID','BranchName','StateName','ClientName','AccountID','Total Cur.Inst.Due']
    missing_cols = [c for c in required_cols if c not in Daily_Clollection.columns]
    if missing_cols:
        st.error(f"Missing columns in Daily Collection file: {missing_cols}")
        st.stop()
    Daily_Clollection = Daily_Clollection[required_cols]

    # Standardize BranchID
    Daily_Clollection['BranchID'] = Daily_Clollection['BranchID'].astype(str).str.zfill(4)
    Daily_Clollection["sub_string"] = Daily_Clollection["AccountID"].str.replace(r'[^A-Za-z]', '', regex=True)

    # Split IGL and TW
    TW = Daily_Clollection[Daily_Clollection['sub_string'].str.startswith("TW")].copy()
    IGL = Daily_Clollection[~Daily_Clollection['sub_string'].str.startswith("TW")].copy()

    IGL['Total Cur.Inst.Due_sum'] = IGL.groupby('ClientID')['Total Cur.Inst.Due'].transform('sum')
    TW['Total Cur.Inst.Due_sum'] = TW.groupby('ClientID')['Total Cur.Inst.Due'].transform('sum')

    IGL.drop_duplicates('ClientID', keep='first', inplace=True)
    TW.drop_duplicates('ClientID', keep='first', inplace=True)

    # Read Branch
    branch = pd.read_excel(branch_file)
    branch.columns = branch.columns.str.strip()
    branch['OurBranchID'] = branch['OurBranchID'].astype(str).str.zfill(4)
    branch.rename({'OurBranchID':'BranchID'}, inplace=True, axis=1)
    IGL = pd.merge(IGL, branch[['BranchID','Lang']], on='BranchID', how='left')
    TW = pd.merge(TW, branch[['BranchID','Lang']], on='BranchID', how='left')

    # Read Mobile
    mobile = pd.read_csv(mobile_file, encoding='ISO-8859-1', low_memory=False)
    mobile.columns = mobile.columns.str.strip()
    mobile.rename({'clientid':'ClientID'}, inplace=True, axis=1)
    mobile['Mobile'] = mobile['Mobile'].astype('Int64')
    IGL = pd.merge(IGL, mobile[['ClientID','Mobile']], on='ClientID', how='left')
    TW = pd.merge(TW, mobile[['ClientID','Mobile']], on='ClientID', how='left')

    IGL = IGL[IGL['Total Cur.Inst.Due_sum'] != 0]
    TW = TW[TW['Total Cur.Inst.Due_sum'] != 0]

    # Add columns
    IGL['TemplateID'] = 'Loan Installment-Good Standing-short'
    TW['TemplateID'] = 'Loan Installment-Good Standing-short'
    IGL['ProductID'] = 'IGL'
    TW['ProductID'] = 'TWL'
    IGL['AccountID'] = pd.NA
    TW['AccountID'] = pd.NA
    IGL['Mobile1'] = 'NULL'
    TW['Mobile1'] = 'NULL'
    IGL['Mobile2'] = 'NULL'
    TW['Mobile2'] = 'NULL'

    IGL.rename({'ClientID':'tag5','Lang':'Language'}, inplace=True, axis=1)
    TW.rename({'ClientID':'tag5','Lang':'Language'}, inplace=True, axis=1)

    IGL["Demand Date"] = pd.to_datetime(manual_date)
    TW["Demand Date"] = pd.to_datetime(manual_date)

    # ----------------------------
    # Drop original 'Total Cur.Inst.Due' to avoid duplicates
    if 'Total Cur.Inst.Due' in IGL.columns:
        IGL.drop(columns=['Total Cur.Inst.Due'], inplace=True)
    if 'Total Cur.Inst.Due' in TW.columns:
        TW.drop(columns=['Total Cur.Inst.Due'], inplace=True)

    # Rename summed column
    IGL.rename({'Total Cur.Inst.Due_sum':'Total Cur.Inst.Due'}, inplace=True, axis=1)
    TW.rename({'Total Cur.Inst.Due_sum':'Total Cur.Inst.Due'}, inplace=True, axis=1)

    IGL = IGL[['BranchID', 'BranchName', 'StateName', 'Language','Demand Date' , 'AccountID',
               'Mobile', 'Mobile1', 'Mobile2', 'Total Cur.Inst.Due', 'tag5', 'ProductID', 'TemplateID']]

    TW = TW[['BranchID', 'BranchName', 'StateName', 'Language','Demand Date' , 'AccountID',
             'Mobile', 'Mobile1', 'Mobile2', 'Total Cur.Inst.Due', 'tag5', 'ProductID', 'TemplateID']]

    # ----------------------------
    # 📈 Dashboard
    # ----------------------------
    st.subheader("Data Overview After Processing")
    st.markdown(f"**IGL Records:** {IGL.shape[0]}  |  **TW Records:** {TW.shape[0]}")

    st.markdown("**IGL Sample Data:**")
    st.dataframe(IGL.head(10))

    st.markdown("**TW Sample Data:**")
    st.dataframe(TW.head(10))

    # Total Due Bar Chart
    st.subheader("Total Due by Product")
    total_due = pd.DataFrame({
        "Product": ["IGL", "TWL"],
        "Total Due": [IGL['Total Cur.Inst.Due'].sum(), TW['Total Cur.Inst.Due'].sum()]
    })
    st.bar_chart(total_due.set_index('Product'))

    # ----------------------------
    # 💾 Download Files
    # ----------------------------
    st.subheader("Download Processed Files")

    def to_excel_bytes(df):
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        return output.getvalue()

    st.download_button("Download IGL Excel", data=to_excel_bytes(IGL), file_name="IGL.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.download_button("Download TW Excel", data=to_excel_bytes(TW), file_name="TW.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

else:
    st.info("📌 Please upload all required files to process the data.")
