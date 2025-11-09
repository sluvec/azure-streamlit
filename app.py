import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# Konfiguracja strony
st.set_page_config(
    page_title="Sales Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    h1 {
        color: #1f77b4;
        padding-bottom: 20px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# Funkcja generująca przykładowe dane
@st.cache_data
def generate_sample_data():
    np.random.seed(42)

    # Generowanie dat dla ostatnich 12 miesięcy
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')

    # Produkty
    products = ['Laptop', 'Smartphone', 'Tablet', 'Headphones', 'Smartwatch',
                'Monitor', 'Keyboard', 'Mouse', 'Camera', 'Speakers']

    # Kategorie
    categories = {
        'Laptop': 'Computers',
        'Smartphone': 'Mobile',
        'Tablet': 'Mobile',
        'Headphones': 'Audio',
        'Smartwatch': 'Wearables',
        'Monitor': 'Computers',
        'Keyboard': 'Accessories',
        'Mouse': 'Accessories',
        'Camera': 'Photography',
        'Speakers': 'Audio'
    }

    # Regiony
    regions = ['North America', 'Europe', 'Asia', 'South America', 'Africa']

    # Generowanie transakcji
    data = []
    for _ in range(5000):
        date = np.random.choice(dates)
        product = np.random.choice(products)
        category = categories[product]
        region = np.random.choice(regions)
        quantity = np.random.randint(1, 10)

        # Ceny bazowe dla produktów
        base_prices = {
            'Laptop': 1200, 'Smartphone': 800, 'Tablet': 500,
            'Headphones': 150, 'Smartwatch': 300, 'Monitor': 400,
            'Keyboard': 100, 'Mouse': 50, 'Camera': 900, 'Speakers': 200
        }

        price = base_prices[product] * (1 + np.random.uniform(-0.2, 0.2))
        revenue = price * quantity

        data.append({
            'Date': date,
            'Product': product,
            'Category': category,
            'Region': region,
            'Quantity': quantity,
            'Price': round(price, 2),
            'Revenue': round(revenue, 2)
        })

    df = pd.DataFrame(data)
    df['Date'] = pd.to_datetime(df['Date'])
    df['Month'] = df['Date'].dt.to_period('M').astype(str)
    df['Year'] = df['Date'].dt.year

    return df

# Wczytanie danych
df = generate_sample_data()

# Sidebar - Filtry
st.sidebar.header("📊 Dashboard Filters")

# Filtr daty
min_date = df['Date'].min().date()
max_date = df['Date'].max().date()
date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Filtr regionu
all_regions = ['All'] + sorted(df['Region'].unique().tolist())
selected_region = st.sidebar.selectbox("Select Region", all_regions)

# Filtr kategorii
all_categories = ['All'] + sorted(df['Category'].unique().tolist())
selected_category = st.sidebar.selectbox("Select Category", all_categories)

# Filtr produktu
all_products = ['All'] + sorted(df['Product'].unique().tolist())
selected_product = st.sidebar.selectbox("Select Product", all_products)

# Aplikowanie filtrów
filtered_df = df.copy()

if len(date_range) == 2:
    start_date, end_date = date_range
    filtered_df = filtered_df[
        (filtered_df['Date'].dt.date >= start_date) &
        (filtered_df['Date'].dt.date <= end_date)
    ]

if selected_region != 'All':
    filtered_df = filtered_df[filtered_df['Region'] == selected_region]

if selected_category != 'All':
    filtered_df = filtered_df[filtered_df['Category'] == selected_category]

if selected_product != 'All':
    filtered_df = filtered_df[filtered_df['Product'] == selected_product]

# Nagłówek
st.title("📊 Sales Analytics Dashboard")
st.markdown("### Real-time Business Intelligence & Analytics")

# Metryki KPI
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_revenue = filtered_df['Revenue'].sum()
    st.metric(
        label="💰 Total Revenue",
        value=f"${total_revenue:,.0f}",
        delta=f"{len(filtered_df)} transactions"
    )

with col2:
    avg_order_value = filtered_df['Revenue'].mean()
    st.metric(
        label="📈 Avg Order Value",
        value=f"${avg_order_value:,.2f}",
        delta="+12.5%"
    )

with col3:
    total_quantity = filtered_df['Quantity'].sum()
    st.metric(
        label="📦 Units Sold",
        value=f"{total_quantity:,}",
        delta="+8.3%"
    )

with col4:
    unique_products = filtered_df['Product'].nunique()
    st.metric(
        label="🛍️ Products",
        value=f"{unique_products}",
        delta=f"{len(filtered_df['Region'].unique())} regions"
    )

st.markdown("---")

# Tabs dla różnych widoków
tab1, tab2, tab3, tab4 = st.tabs(["📈 Trends", "🌍 Regional Analysis", "📊 Product Performance", "📋 Data Table"])

with tab1:
    st.subheader("Revenue Trends Over Time")

    # Przygotowanie danych dla wykresu czasowego
    monthly_revenue = filtered_df.groupby('Month')['Revenue'].sum().reset_index()
    monthly_revenue['Month'] = pd.to_datetime(monthly_revenue['Month'])

    fig_trend = px.line(
        monthly_revenue,
        x='Month',
        y='Revenue',
        title='Monthly Revenue Trend',
        markers=True
    )
    fig_trend.update_layout(
        xaxis_title="Month",
        yaxis_title="Revenue ($)",
        hovermode='x unified'
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        # Sprzedaż według kategorii w czasie
        category_trend = filtered_df.groupby(['Month', 'Category'])['Revenue'].sum().reset_index()
        category_trend['Month'] = pd.to_datetime(category_trend['Month'])

        fig_category_trend = px.area(
            category_trend,
            x='Month',
            y='Revenue',
            color='Category',
            title='Revenue by Category Over Time'
        )
        st.plotly_chart(fig_category_trend, use_container_width=True)

    with col2:
        # Ilość transakcji w czasie
        daily_transactions = filtered_df.groupby('Date').size().reset_index(name='Transactions')

        fig_transactions = px.bar(
            daily_transactions,
            x='Date',
            y='Transactions',
            title='Daily Transactions Volume'
        )
        st.plotly_chart(fig_transactions, use_container_width=True)

with tab2:
    st.subheader("Regional Performance Analysis")

    col1, col2 = st.columns(2)

    with col1:
        # Revenue by region - Pie chart
        region_revenue = filtered_df.groupby('Region')['Revenue'].sum().reset_index()

        fig_region_pie = px.pie(
            region_revenue,
            values='Revenue',
            names='Region',
            title='Revenue Distribution by Region',
            hole=0.4
        )
        st.plotly_chart(fig_region_pie, use_container_width=True)

    with col2:
        # Units sold by region - Bar chart
        region_units = filtered_df.groupby('Region')['Quantity'].sum().reset_index()
        region_units = region_units.sort_values('Quantity', ascending=True)

        fig_region_bar = px.bar(
            region_units,
            x='Quantity',
            y='Region',
            orientation='h',
            title='Units Sold by Region',
            color='Quantity',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_region_bar, use_container_width=True)

    # Szczegółowa tabela regionalna
    st.subheader("Regional Statistics")
    regional_stats = filtered_df.groupby('Region').agg({
        'Revenue': ['sum', 'mean'],
        'Quantity': 'sum',
        'Product': 'count'
    }).round(2)
    regional_stats.columns = ['Total Revenue', 'Avg Order Value', 'Total Units', 'Transactions']
    regional_stats = regional_stats.sort_values('Total Revenue', ascending=False)
    st.dataframe(regional_stats, use_container_width=True)

with tab3:
    st.subheader("Product Performance Metrics")

    col1, col2 = st.columns(2)

    with col1:
        # Top produkty według revenue
        top_products = filtered_df.groupby('Product')['Revenue'].sum().sort_values(ascending=False).head(10).reset_index()

        fig_top_products = px.bar(
            top_products,
            x='Revenue',
            y='Product',
            orientation='h',
            title='Top 10 Products by Revenue',
            color='Revenue',
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig_top_products, use_container_width=True)

    with col2:
        # Średnia cena vs ilość sprzedanych jednostek
        product_metrics = filtered_df.groupby('Product').agg({
            'Price': 'mean',
            'Quantity': 'sum'
        }).reset_index()

        fig_scatter = px.scatter(
            product_metrics,
            x='Price',
            y='Quantity',
            size='Quantity',
            color='Product',
            title='Price vs Quantity Sold',
            hover_data=['Product']
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    # Category performance
    st.subheader("Category Performance")
    category_stats = filtered_df.groupby('Category').agg({
        'Revenue': 'sum',
        'Quantity': 'sum',
        'Product': 'count'
    }).round(2)
    category_stats.columns = ['Total Revenue', 'Total Units', 'Transactions']
    category_stats['Avg Transaction Value'] = (category_stats['Total Revenue'] / category_stats['Transactions']).round(2)
    category_stats = category_stats.sort_values('Total Revenue', ascending=False)

    st.dataframe(category_stats, use_container_width=True)

with tab4:
    st.subheader("Detailed Transaction Data")

    # Opcje wyświetlania
    col1, col2, col3 = st.columns(3)

    with col1:
        show_rows = st.selectbox("Rows to display", [10, 25, 50, 100, 500])

    with col2:
        sort_column = st.selectbox("Sort by", filtered_df.columns.tolist())

    with col3:
        sort_order = st.radio("Order", ["Descending", "Ascending"])

    # Sortowanie
    ascending = sort_order == "Ascending"
    display_df = filtered_df.sort_values(by=sort_column, ascending=ascending).head(show_rows)

    # Wyświetlenie tabeli
    st.dataframe(
        display_df.style.format({
            'Price': '${:.2f}',
            'Revenue': '${:.2f}',
            'Date': lambda x: x.strftime('%Y-%m-%d')
        }),
        use_container_width=True
    )

    # Statystyki podsumowujące
    st.subheader("Summary Statistics")
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Revenue Statistics**")
        st.write(filtered_df['Revenue'].describe().round(2))

    with col2:
        st.write("**Quantity Statistics**")
        st.write(filtered_df['Quantity'].describe().round(2))

    # Opcja pobrania danych
    st.download_button(
        label="📥 Download Data as CSV",
        data=filtered_df.to_csv(index=False).encode('utf-8'),
        file_name=f'sales_data_{datetime.now().strftime("%Y%m%d")}.csv',
        mime='text/csv'
    )

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>📊 Sales Analytics Dashboard | Data updated in real-time | Built with Streamlit & Plotly</p>
    </div>
    """, unsafe_allow_html=True)
