import streamlit as st
import pandas as pd
import time
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from io import BytesIO

st.set_page_config(page_title="Mohiuddin Nagar Constituency (137)", layout="wide")

PANCHAYATS_DATA = {
    "Select Block": [],
    "Mohiuddin Nagar Block": [
        "Bhadaia", "Bochaha", "Dubaha", "Harail", "Kalyanpur Basti West",
        "Karim Nagar", "Kalyanpur Basti East", "Kursaha", "Madudabad",
        "MohiuddinNagar North", "MohiuddinNagar South", "Mohmadipur",
        "Raja Jan", "Raspur Patasia East", "Raspur Patasia West",
        "Siwasingh Pur", "Tetar Pur"
    ],
    "Mohanpur Block": [
        "Baghara", "Dasahra", "Dharni Patti West", "Dharni Patti East",
        "Dumri South", "Dumri North", "Jalalpur", "Madhupur Sarai",
        "Mohanpur", "Rajpur", "Bishanpur Ber"
    ],
    "Patori Block": [
        "Dhamaun North", "Dhamaun South", "Hetanpur", "Inaetpur",
        "Rupauli", "Shiura", "Tara Dhamaun", "Chaksaho"
    ]
}

BLOCKS = list(PANCHAYATS_DATA.keys())[1:]
ALL_PANCHAYATS = sorted(list(set([p for panchayats in PANCHAYATS_DATA.values() for p in panchayats])))

@st.cache_resource
def init_db():
    try:
        client = MongoClient(st.secrets["mongodb"]["uri"])
        return client.constituency_db
    except Exception as e:
        st.error(f"Error connecting to MongoDB: {e}")
        return None

def add_or_update_data(data, record_id=None):
    db = init_db()
    if db is not None:
        try:
            if record_id:
                db.constituency_data.update_one(
                    {"_id": ObjectId(record_id)},
                    {"$set": data}
                )
            else:
                data["created_at"] = datetime.utcnow()
                db.constituency_data.insert_one(data)
            return True
        except Exception as e:
            st.error(f"Error saving data: {e}")
    return False

def get_filtered_data(filters=None):
    db = init_db()
    if db is not None:
        try:
            query = {k: v for k, v in (filters or {}).items() if v}
            data = list(db.constituency_data.find(query))
            for doc in data:
                doc['id'] = str(doc.pop('_id'))
            return pd.DataFrame(data)
        except Exception as e:
            st.error(f"Error fetching data: {e}")
    return pd.DataFrame()

def delete_record(record_id):
    db = init_db()
    if db is not None:
        try:
            db.constituency_data.delete_one({"_id": ObjectId(record_id)})
            return True
        except Exception as e:
            st.error(f"Error deleting record: {e}")
    return False

def export_to_pdf(df):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=15,
        rightMargin=15,
        topMargin=50,  # Increased for title
        bottomMargin=25
    )
    elements = []
    
    # Add title
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=getSampleStyleSheet()['Heading1'],
        fontSize=16,
        alignment=1,  # Center alignment
        spaceAfter=30
    )
    title = Paragraph("<b>Mohiuddin Nagar Constituency (137)</b>", title_style)
    elements.append(title)
    
    # Create custom styles for each column
    styles = getSampleStyleSheet()
    
    # Custom style for cells with strict width control
    cell_style = ParagraphStyle(
        'CustomCell',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        alignment=TA_LEFT,
        wordWrap='CJK',
        splitLongWords=1
    )
    
    # Header style
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.whitesmoke,
        fontName='Helvetica-Bold'
    )
    
    # Define headers
    headers = [
        Paragraph('Name', header_style),
        Paragraph('Block', header_style),
        Paragraph('Panchayat', header_style),
        Paragraph('Designation', header_style),
        Paragraph('Mobile', header_style),
        Paragraph('Address', header_style)
    ]
    data = [headers]
    
    # Process data rows
    for _, row in df.iterrows():
        data.append([
            Paragraph(str(row['name']).strip() or '-', cell_style),
            Paragraph(str(row['block']).strip() or '-', cell_style),
            Paragraph(str(row['panchayat']).strip() or '-', cell_style),
            Paragraph(str(row['designation']).strip() or '-', cell_style),
            Paragraph(str(row['mobile_number']).strip() or '-', cell_style),
            Paragraph(str(row['address']).strip() or '-', cell_style)
        ])
    
    # Fixed column widths (total = 762)
    col_widths = [110, 110, 110, 90, 82, 260]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    
    style = TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.2)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.Color(0.95, 0.95, 0.95), colors.white])
    ])
    
    table.setStyle(style)
    elements.append(table)
    doc.build(elements)
    
    return buffer.getvalue()

def data_entry_form(existing_data=None):
    existing_data = {} if existing_data is None else existing_data.to_dict() if hasattr(existing_data, 'to_dict') else existing_data
    
    with st.form(key="entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            vidhan_sabha = st.text_input("Vidhan Sabha", value="Mohiuddin Nagar")
            selected_block = st.selectbox(
                "Block",
                ["Select Block"] + BLOCKS,
                index=BLOCKS.index(existing_data.get('block')) + 1 if existing_data.get('block') in BLOCKS else 0
            )
            selected_panchayat = st.selectbox(
                "Panchayat",
                ["Select Panchayat"] + ALL_PANCHAYATS,
                index=ALL_PANCHAYATS.index(existing_data.get('panchayat')) + 1 if existing_data.get('panchayat') in ALL_PANCHAYATS else 0
            )
            name = st.text_input("Name", value=existing_data.get('name', ''))

        with col2:
            designation = st.text_input("Designation (Optional)", value=existing_data.get('designation', ''))
            mobile_number = st.text_input("Mobile Number (Optional)", value=existing_data.get('mobile_number', ''), max_chars=10)
            address = st.text_area("Address (Optional)", value=existing_data.get('address', ''))

        submit_button = st.form_submit_button(
            label="Update" if existing_data else "Submit",
            use_container_width=True
        )

        if submit_button:
            if selected_block == "Select Block":
                st.error("Please select a Block")
                return False
            if selected_panchayat == "Select Panchayat":
                st.error("Please select a Panchayat")
                return False
            if not name:
                st.error("Please enter a Name")
                return False
            
            if mobile_number and not (len(mobile_number) == 10 and mobile_number.isdigit()):
                st.error("Please enter a valid 10-digit mobile number")
                return False

            data = {
                "vidhan_sabha": vidhan_sabha,
                "block": selected_block,
                "panchayat": selected_panchayat,
                "name": name,
                "designation": designation,
                "address": address,
                "mobile_number": mobile_number
            }
            
            record_id = existing_data.get('id') if existing_data else None
            
            with st.spinner('Processing...'):
                if add_or_update_data(data, record_id):
                    st.balloons()
                    st.success(f"✅ Data {'updated' if existing_data else 'submitted'} successfully!")
                    time.sleep(1)
                    return True
    
    return False

def admin_view():
    st.header("👥 Data View")
    
    # Password protection
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    # Add logout button when authenticated
    if st.session_state.authenticated:
        if st.sidebar.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()
    
    if not st.session_state.authenticated:
        password = st.text_input("Enter password to view data", type="password")
        if password:
            if password in ["221067", "210500"]:
                st.session_state.authenticated = True
                st.success("Access granted!")
                st.rerun()
            else:
                st.error("Incorrect password")
        return
        
    # Initialize session state for modify mode
    if 'modify_mode' not in st.session_state:
        st.session_state.modify_mode = False
    
    # Add custom CSS
    st.markdown("""
        <style>
        .modify-button {
            text-align: right;
            padding: 1rem 0;
        }
        .record-container {
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 8px;
            margin: 4px 0;
        }
        .record-name { font-weight: 600; }
        .small-button {
            font-size: 12px !important;
            padding: 0px 4px !important;
            height: 25px !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Search filters in a row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        filter_block = st.selectbox("Filter by Block", ["All"] + BLOCKS, key="admin_block")
    with col2:
        filter_panchayat = st.selectbox("Filter by Panchayat", ["All"] + ALL_PANCHAYATS, key="admin_panchayat")
    with col3:
        name_search = st.text_input("Search by Name")
    with col4:
        designation_search = st.text_input("Search by Designation")

    # Toggle modify mode button
    col1, col2, col3 = st.columns([3, 1, 1])
    with col3:
        if st.button("🔧 Modify Records" if not st.session_state.modify_mode else "🔙 Back to View",
                    type="primary" if not st.session_state.modify_mode else "secondary"):
            st.session_state.modify_mode = not st.session_state.modify_mode
            st.rerun()

    # Apply filters
    filters = {}
    if filter_block != "All":
        filters["block"] = filter_block
    if filter_panchayat != "All":
        filters["panchayat"] = filter_panchayat
    if name_search:
        filters["name"] = {"$regex": name_search, "$options": "i"}
    if designation_search:
        filters["designation"] = {"$regex": designation_search, "$options": "i"}

    df = get_filtered_data(filters)
    
    if not df.empty:
        # Normal View Mode
        if not st.session_state.modify_mode:
            st.dataframe(
                df[['name', 'block', 'panchayat', 'designation', 'mobile_number', 'address']],
                use_container_width=True,
                height=400
            )
            
            # Download buttons
            col1, col2, col3 = st.columns([4, 1, 1])
            with col2:
                if st.button("📄 Download PDF", use_container_width=True):
                    pdf_data = export_to_pdf(df)
                    st.download_button(
                        label="Click to Download PDF",
                        data=pdf_data,
                        file_name="constituency_data.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            with col3:
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📊 Download CSV",
                    data=csv,
                    file_name="constituency_data.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        # Modify Mode
        else:
            for idx, row in df.iterrows():
                st.markdown(f"""
                    <div class="record-container>
                            <div class="record-container">
                        <div class="record-name">{row['name']}</div>
                        <div>{row['block']} | {row['panchayat']}</div>
                        <div>{row.get('designation', '')} {' | ' if row.get('designation') else ''}{row.get('mobile_number', '')}</div>
                        <div>{row.get('address', '')}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("✏️ Edit", key=f"edit_{row['id']}", use_container_width=True):
                        st.session_state.editing_record = row
                        st.session_state.current_page = 'data_entry'
                        st.rerun()
                with col2:
                    if st.button("🗑️ Delete", key=f"delete_{row['id']}", use_container_width=True):
                        if delete_record(row['id']):
                            with st.spinner('Deleting...'):
                                time.sleep(0.5)
                                st.success("✅ Record deleted successfully!")
                                time.sleep(0.5)
                                st.rerun()
    else:
        st.info("No data available for the selected filters")

def main():
    st.title("🏛️ Mohiuddin Nagar Constituency Management System (137)")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        data_entry_btn = st.button("📝 Data Entry", type="primary", use_container_width=True)
    with col2:
        admin_view_btn = st.button("👥 Data View", type="primary", use_container_width=True)

    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'data_entry'
    if 'editing_record' not in st.session_state:
        st.session_state.editing_record = None
    if 'modify_mode' not in st.session_state:
        st.session_state.modify_mode = False

    if data_entry_btn:
        st.session_state.current_page = 'data_entry'
        st.session_state.editing_record = None
        st.session_state.modify_mode = False
    if admin_view_btn:
        st.session_state.current_page = 'admin_view'
        st.session_state.editing_record = None
        st.session_state.modify_mode = False

    st.divider()

    if st.session_state.current_page == 'data_entry':
        if st.session_state.editing_record is not None:
            st.header("📝 Edit Record")
            if data_entry_form(st.session_state.editing_record):
                st.session_state.editing_record = None
                st.rerun()
        else:
            st.header("📝 Data Entry Form")
            if data_entry_form():
                st.rerun()
    else:
        admin_view()

if __name__ == "__main__":
    main()