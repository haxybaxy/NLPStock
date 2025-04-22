import streamlit as st
import os
import sys
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import json
from pathlib import Path
import logging
import random

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('streamlit_app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import project modules
from utils.portfolio_manager import PortfolioManager
from data_fetchers.stock_price_fetcher import update_portfolio_data, get_stock_info, fetch_stock_data
from stock_analyzer import StockAnalyzer

# Set page configuration
st.set_page_config(
    page_title="NLPStock Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize components
portfolio_manager = PortfolioManager()
stock_analyzer = StockAnalyzer()

# Define color schemes for UI
COLOR_GAIN = "#4CAF50"
COLOR_LOSS = "#FF5252"
BACKGROUND_COLOR = "#f0f2f6"

# Helper functions
def load_portfolio_data():
    portfolio_path = Path("STOCK_DB/prices/portfolio_data.json")
    if not portfolio_path.exists():
        return {}
    
    try:
        with open(portfolio_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading portfolio data: {e}")
        return {}

def format_large_number(num):
    if num >= 1_000_000_000:
        return f"${num / 1_000_000_000:.2f}B"
    elif num >= 1_000_000:
        return f"${num / 1_000_000:.2f}M"
    elif num >= 1_000:
        return f"${num / 1_000:.2f}K"
    else:
        return f"${num:.2f}"

def load_stock_analysis(symbol):
    """Load analysis data for a specific stock"""
    # Try to load from analysis directory
    analysis_path = Path(f"STOCK_DB/analysis/{symbol}_analysis.json")
    if analysis_path.exists():
        try:
            with open(analysis_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading analysis for {symbol}: {e}")
    
    return None

def load_nlp_data(symbol):
    """Load NLP processed data for a specific stock"""
    nlp_path = Path(f"STOCK_DB/nlp_data/{symbol}_nlp_data.json")
    if nlp_path.exists():
        try:
            with open(nlp_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading NLP data for {symbol}: {e}")
    
    return None

def get_change_color(change):
    """Return color based on positive or negative change"""
    return COLOR_GAIN if change >= 0 else COLOR_LOSS

def safe_get_price(price_data, date_key, field="Close", default=0):
    """Safely get price data for a date, with error handling"""
    try:
        if not date_key or not price_data:
            return default
            
        if date_key in price_data:
            data_point = price_data[date_key]
            
            # First, try to find tuple keys that match our pattern: (field, symbol)
            for key in data_point:
                # Check for string representation of tuple like "('Close', 'AAPL')"
                if isinstance(key, str) and key.startswith("('") and field in key:
                    logger.info(f"Found tuple-like key: {key}")
                    return float(data_point[key])
                    
                # Check for actual tuple
                elif isinstance(key, tuple) and len(key) == 2 and key[0] == field:
                    logger.info(f"Found tuple key: {key}")
                    return float(data_point[key])
            
            # If no tuple keys found, try direct field match
            if field in data_point:
                return float(data_point[field])
                
        # Log the issue
        logger.warning(f"Could not find {field} price for date {date_key}, returning default {default}")
        return default
    except Exception as e:
        logger.error(f"Error in safe_get_price for date {date_key}, field {field}: {e}")
        return default

def calculate_daily_change(price_data, symbol):
    """Calculate the daily percentage change (yesterday vs today)"""
    try:
        if not price_data or len(price_data) < 2:
            return 0
            
        # Sort dates chronologically
        dates = sorted(price_data.keys(), key=lambda d: datetime.strptime(d, '%Y-%m-%d'))
        
        if len(dates) < 2:
            return 0
            
        # Get the most recent and previous day's data
        latest_date = dates[-1]
        prev_date = dates[-2]
        
        latest_close = safe_get_price(price_data, latest_date, "Close", 0)
        prev_close = safe_get_price(price_data, prev_date, "Close", 0)
        
        # Avoid division by zero
        if prev_close <= 0:
            return 0
            
        # Calculate percentage change
        daily_change = ((latest_close - prev_close) / prev_close) * 100
        logger.info(f"Daily change for {symbol}: {daily_change:.2f}% (from {prev_date} to {latest_date})")
        return daily_change
        
    except Exception as e:
        logger.error(f"Error calculating daily change for {symbol}: {e}")
        return 0

# App title with custom styling
st.markdown("""
<div style="text-align: center; padding: 10px; background-color: #1E1E1E; border-radius: 10px; margin-bottom: 20px;">
    <h1 style="color: white;">📊 NLPStock Analyzer</h1>
    <p style="color: #B0B0B0;">AI-powered stock movement analysis based on news</p>
</div>
""", unsafe_allow_html=True)

# Load portfolio data early, but calculate stats later
portfolio_data = load_portfolio_data()

# Load quantities if available
quantities = {}
quantities_path = Path("STOCK_DB/portfolios/quantities.json")
if quantities_path.exists():
    try:
        with open(quantities_path, 'r') as f:
            quantities = json.load(f)
    except Exception as e:
        logger.error(f"Error loading quantities: {e}")

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/stocks.png", width=80)
    st.header("Portfolio Management")

    # Portfolio selection
    portfolios = portfolio_manager.list_portfolios()
    selected_portfolio = st.selectbox("Select Portfolio", portfolios, index=0)

    # Add stocks form
    with st.form("add_stock_form"):
        new_stock = st.text_input("Add Stock Symbol").upper()
        submitted = st.form_submit_button("Add to Portfolio")
        if submitted and new_stock:
            if portfolio_manager.add_stock(new_stock, selected_portfolio):
                st.success(f"Added {new_stock} to portfolio")
            else:
                st.info(f"{new_stock} is already in portfolio")

    # Get portfolio symbols
    portfolio_symbols = portfolio_manager.get_portfolio_symbols(selected_portfolio)

    # Update data button
    if st.button("📊 Update Portfolio Data", use_container_width=True):
        with st.spinner("Updating portfolio data..."):
            updated_data = stock_analyzer.update_portfolio_stocks(selected_portfolio)
            if updated_data:
                st.success(f"Updated data for {len(updated_data)} stocks")
            else:
                st.warning("No data updated. Portfolio may be empty.")

    # Add a button to generate test data
    if st.button("🧪 Generate Test Data", use_container_width=True):
        with st.spinner("Generating sample price data..."):
            # Create test data directory if it doesn't exist
            prices_dir = Path("STOCK_DB/prices")
            prices_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate sample data
            sample_data = {}
            for symbol in portfolio_symbols:
                # Create realistic looking stock data
                base_price = random.uniform(50, 500)
                prices = {}
                
                # Generate 30 days of price data
                for i in range(30):
                    # Calculate date (going backward from today)
                    date = (datetime.now() - timedelta(days=29-i)).strftime('%Y-%m-%d')
                    
                    # Create small random daily movement (-3% to +3%)
                    daily_change = random.uniform(-0.03, 0.03)
                    if i > 0:
                        # Get previous day's close price
                        prev_date = (datetime.now() - timedelta(days=30-i)).strftime('%Y-%m-%d')
                        prev_close = prices[prev_date]["Close"]
                        # Apply movement to previous close
                        close_price = prev_close * (1 + daily_change)
                    else:
                        close_price = base_price
                    
                    # Create OHLC data
                    high = close_price * random.uniform(1, 1.02)
                    low = close_price * random.uniform(0.98, 1)
                    open_price = random.uniform(low, high)
                    
                    # Create volume
                    volume = random.randint(1000000, 10000000)
                    
                    # Add to prices
                    prices[date] = {
                        "Open": open_price,
                        "High": high,
                        "Low": low,
                        "Close": close_price,
                        "Volume": volume
                    }
                
                # Create stock info
                sample_data[symbol] = {
                    "prices": prices,
                    "info": {
                        "symbol": symbol,
                        "name": f"{symbol} Inc.",
                        "sector": random.choice(["Technology", "Healthcare", "Finance", "Consumer", "Energy"]),
                        "market_cap": random.randint(1000000000, 2000000000000),
                        "pe_ratio": random.uniform(10, 30),
                        "dividend_yield": random.uniform(0, 5),
                        "fifty_two_week_high": base_price * 1.2,
                        "fifty_two_week_low": base_price * 0.8
                    },
                    "last_updated": datetime.now().isoformat()
                }
            
            # Save sample data
            with open(prices_dir / "portfolio_data.json", 'w') as f:
                json.dump(sample_data, f, indent=2)
            
            # Refresh the app
            st.success(f"Generated test data for {len(portfolio_symbols)} stocks")
            st.experimental_rerun()

    # Settings
    st.header("Analysis Settings")
    movement_threshold = st.slider("Movement Threshold (%)", 1.0, 10.0, 2.0, 0.5)

    # Run analysis button
    if st.button("🔍 Analyze Moving Stocks", use_container_width=True):
        with st.spinner("Analyzing stock movements..."):
            results = stock_analyzer.analyze_moving_stocks(selected_portfolio, movement_threshold)
            if results:
                st.success(f"Analysis complete for {len(results)} stocks")
            else:
                st.info("No stocks with significant movement found")

# Now calculate portfolio stats after portfolio_symbols is defined
portfolio_value = 0
avg_portfolio_change = 0

# Calculate portfolio stats if data is available
if portfolio_data and len(portfolio_symbols) > 0:
    valid_stocks = 0
    total_change = 0
    
    # Debug the portfolio data content
    logger.info(f"Portfolio contains {len(portfolio_symbols)} symbols")
    logger.info(f"Portfolio data contains {len(portfolio_data)} stocks")
    
    for symbol in portfolio_symbols:
        if symbol in portfolio_data:
            stock_info = portfolio_data[symbol]["info"]
            price_data = portfolio_data[symbol]["prices"]
            
            # Initialize variables
            latest_date = None
            latest_price = 0
            
            # Get the latest price data with error handling
            if price_data and len(price_data) > 0:
                # Sort dates chronologically to ensure we get the most recent one
                dates = sorted(price_data.keys(), key=lambda d: datetime.strptime(d, '%Y-%m-%d'))
                latest_date = dates[-1]  # Get the most recent date
                latest_price = safe_get_price(price_data, latest_date, "Close", 0)
                logger.info(f"Got price for {symbol} on {latest_date}: ${latest_price}")
                
                # Calculate daily change instead of 10-day average
                daily_change = calculate_daily_change(price_data, symbol)
            
            # Get quantity from stored quantities
            quantity = float(quantities.get(symbol, {}).get(selected_portfolio, 1))
            position_value = latest_price * quantity
            
            if latest_price > 0:
                portfolio_value += position_value
                total_change += daily_change
                valid_stocks += 1
                logger.info(f"Added {symbol} to portfolio value: price=${latest_price:.2f} x {quantity} shares = ${position_value:.2f}, daily change={daily_change:.2f}%")
        else:
            logger.warning(f"Symbol {symbol} not found in portfolio data")
    
    # Calculate average change
    avg_portfolio_change = total_change / valid_stocks if valid_stocks > 0 else 0
    logger.info(f"Portfolio value: ${portfolio_value:.2f}, Avg daily change: {avg_portfolio_change:.2f}%")

# Display portfolio value and change in header
change_color = COLOR_GAIN if avg_portfolio_change >= 0 else COLOR_LOSS
change_arrow = "▲" if avg_portfolio_change >= 0 else "▼"

# Display portfolio stats in the header if we have data
if portfolio_value > 0:
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; margin-bottom: 20px; background-color: #F0F2F6; padding: 10px; border-radius: 10px;">
        <div style="text-align: center; flex: 1;">
            <h3>Portfolio Value</h3>
            <p style="font-size: 24px; font-weight: bold;">${portfolio_value:.2f}</p>
        </div>
        <div style="text-align: center; flex: 1;">
            <h3>Daily Change</h3>
            <p style="font-size: 24px; font-weight: bold; color: {change_color};">{avg_portfolio_change:.2f}% {change_arrow}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Main content
if not portfolio_symbols:
    st.info("Your portfolio is empty. Add some stocks to get started.")
else:
    # Portfolio overview
    st.subheader("Portfolio Overview")
    
    # Add a feature to specify stock quantities
    with st.expander("Edit Stock Quantities", expanded=False):
        st.markdown("Specify how many shares of each stock you own:")
        
        # Create a dict to store quantities
        quantities = {}
        
        # Load existing quantities if available
        quantities_path = Path("STOCK_DB/portfolios/quantities.json")
        if quantities_path.exists():
            try:
                with open(quantities_path, 'r') as f:
                    quantities = json.load(f)
            except Exception as e:
                logger.error(f"Error loading quantities: {e}")
        
        # Create columns for better layout
        col1, col2 = st.columns(2)
        
        # Display input fields for each stock
        updated = False
        for i, symbol in enumerate(portfolio_symbols):
            # Alternate between columns for better layout
            with col1 if i % 2 == 0 else col2:
                # Default to 1 if not specified
                current_quantity = quantities.get(symbol, {}).get(selected_portfolio, 1)
                new_quantity = st.number_input(
                    f"{symbol} Shares", 
                    min_value=0.0, 
                    value=float(current_quantity),
                    step=1.0,
                    format="%.2f",
                    key=f"qty_{symbol}"
                )
                
                # Update quantity if changed
                if new_quantity != current_quantity:
                    if symbol not in quantities:
                        quantities[symbol] = {}
                    quantities[symbol][selected_portfolio] = new_quantity
                    updated = True
        
        # Save button to update quantities
        if st.button("Save Quantities") or updated:
            # Create directory if it doesn't exist
            quantities_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save quantities to file
            try:
                with open(quantities_path, 'w') as f:
                    json.dump(quantities, f, indent=2)
                st.success("Quantities saved successfully!")
            except Exception as e:
                logger.error(f"Error saving quantities: {e}")
                st.error(f"Error saving quantities: {e}")
    
    # Display portfolio data in a table
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Create a table of portfolio stocks with better styling
        data = []
        
        # Check if portfolio data is available
        if not portfolio_data:
            st.warning("No price data available. Please click the 'Generate Test Data' button in the sidebar to create sample data.")
        
        # Display data from each stock
        for symbol in portfolio_symbols:
            if symbol in portfolio_data:
                stock_info = portfolio_data[symbol]["info"]
                price_data = portfolio_data[symbol]["prices"]
                
                # Initialize variables
                latest_date = None
                latest_price = 0
                daily_change = 0
                
                # Get the latest price data with error handling
                if price_data and len(price_data) > 0:
                    # Sort dates chronologically to ensure we get the most recent one
                    dates = sorted(price_data.keys(), key=lambda d: datetime.strptime(d, '%Y-%m-%d'))
                    latest_date = dates[-1]  # Get the most recent date
                    latest_price = safe_get_price(price_data, latest_date, "Close", 0)
                    
                    # Calculate daily change instead of 10-day average
                    daily_change = calculate_daily_change(price_data, symbol)
                
                # Get quantity from stored quantities
                quantity = float(quantities.get(symbol, {}).get(selected_portfolio, 1))
                position_value = latest_price * quantity
                
                data.append({
                    "Symbol": symbol,
                    "Name": stock_info.get("name", symbol),
                    "Quantity": quantity,
                    "Price": round(latest_price, 2) if isinstance(latest_price, (int, float)) else 0,
                    "Position Value": round(position_value, 2) if isinstance(position_value, (int, float)) else 0,
                    "Daily Change (%)": round(daily_change, 2) if isinstance(daily_change, (int, float)) else 0,
                    "Market Cap": format_large_number(stock_info.get("market_cap", 0)),
                    "Sector": stock_info.get("sector", "")
                })
            else:
                data.append({
                    "Symbol": symbol,
                    "Name": symbol,
                    "Quantity": 0,
                    "Price": 0,
                    "Position Value": 0,
                    "Daily Change (%)": 0,
                    "Market Cap": "N/A",
                    "Sector": "N/A"
                })
        
        if data:
            df = pd.DataFrame(data)
            
            # Apply styling to the dataframe
            def highlight_change(val):
                try:
                    val_float = float(val)
                    color = COLOR_GAIN if val_float >= 0 else COLOR_LOSS
                    return f'color: {color}; font-weight: bold'
                except (ValueError, TypeError):
                    return ''
            
            def format_price(val):
                try:
                    return f'${float(val):.2f}'
                except (ValueError, TypeError):
                    return val
            
            def format_pct(val):
                try:
                    return f'{float(val):.2f}%'
                except (ValueError, TypeError):
                    return val
            
            def format_quantity(val):
                try:
                    return f'{float(val):,.2f}'
                except (ValueError, TypeError):
                    return val
            
            # Convert numeric columns to float for proper sorting
            for col in ['Price', 'Daily Change (%)', 'Position Value', 'Quantity']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Format the dataframe with styling
            styled_df = df.style.format({
                'Quantity': format_quantity,
                'Price': format_price,
                'Position Value': format_price,
                'Daily Change (%)': format_pct
            }).applymap(
                highlight_change, 
                subset=['Daily Change (%)']
            )
            
            st.dataframe(styled_df, use_container_width=True)
    
    with col2:
        # Some portfolio stats with better styling
        if data:
            num_stocks = len(data)
            num_sectors = len(set(item["Sector"] for item in data if item["Sector"] != "N/A"))
            
            # Use the already calculated portfolio value and average change
            st.metric("💰 Portfolio Value", f"${portfolio_value:.2f}")
            st.metric("📊 Daily Change", f"{avg_portfolio_change:.2f}%", 
                     delta=f"{avg_portfolio_change:.2f}%",
                     delta_color="normal")
            st.metric("📈 Stocks", num_stocks)
            st.metric("🏢 Sectors", num_sectors)
    
    # Moving Stocks Analysis with enhanced UI
    st.markdown("""
    <div style="padding: 10px; background-color: #1E1E1E; border-radius: 10px; margin: 20px 0;">
        <h2 style="color: white;">📈 Stock Movement Analysis (Daily Change)</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Find analysis files
    analysis_dir = Path("STOCK_DB/analysis")
    analysis_files = list(analysis_dir.glob("*_analysis.json")) if analysis_dir.exists() else []
    
    if not analysis_files:
        st.info("No stock analysis available yet. Click 'Analyze Moving Stocks' to generate insights.")
    else:
        # Get and display analysis
        analyses = []
        for file in analysis_files:
            try:
                with open(file, 'r') as f:
                    analysis = json.load(f)
                    symbol = analysis.get("symbol", "")
                    if symbol in portfolio_symbols:
                        analyses.append(analysis)
            except Exception as e:
                logger.error(f"Error loading analysis file {file}: {e}")
        
        if not analyses:
            st.info("No analysis found for current portfolio stocks.")
        else:
            # Update the movers analysis section to use daily changes
            for analysis in analyses:
                symbol = analysis.get("symbol", "")
                if symbol in portfolio_data:
                    price_data = portfolio_data[symbol]["prices"]
                    if price_data and len(price_data) > 0:
                        # Calculate daily change instead of 10-day average
                        daily_change = calculate_daily_change(price_data, symbol)
                        
                        # Update the analysis with daily change
                        analysis["daily_change_percentage"] = daily_change
                        analysis["type"] = "gainer" if daily_change >= 0 else "loser"
                        
                        logger.info(f"Updated {symbol} daily change to {daily_change:.2f}%")
            
            # Sort by absolute change percentage
            analyses.sort(key=lambda x: abs(x.get("daily_change_percentage", 0)), reverse=True)
            
            # Create tabs for each analysis
            tabs = st.tabs([f"{a['symbol']} ({a.get('daily_change_percentage', 0):.2f}%)" for a in analyses])
            
            for i, (tab, analysis) in enumerate(zip(tabs, analyses)):
                with tab:
                    symbol = analysis.get("symbol", "")
                    change = analysis.get("daily_change_percentage", 0)
                    summary = analysis.get("summary", "No summary available")
                    change_type = analysis.get("type", "neutral")
                    
                    # Load NLP data if available
                    nlp_data = load_nlp_data(symbol)
                    
                    # Define colors based on change type
                    color = COLOR_GAIN if change_type == "gainer" else COLOR_LOSS if change_type == "loser" else "#3366FF"
                    
                    # Create a nice header for the stock
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; margin-bottom: 20px;">
                        <div style="font-size: 36px; margin-right: 15px;">{'📈' if change_type == 'gainer' else '📉' if change_type == 'loser' else '📊'}</div>
                        <div>
                            <h1 style="margin: 0; color: {color};">{symbol}</h1>
                            <p style="margin: 0; font-size: 18px; color: {color};">Daily Change: {change:.2f}% {'▲' if change >= 0 else '▼'}</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Display summary in an expander
                    with st.expander("📝 Summary of Why It's Moving", expanded=True):
                        st.markdown(f"""
                        <div style="background-color: #F0F2F6; padding: 15px; border-radius: 10px; border-left: 5px solid {color};">
                            {summary}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Display price chart
                    if symbol in portfolio_data:
                        price_data = portfolio_data[symbol]["prices"]
                        if price_data:
                            st.subheader("📈 Recent Price Activity")
                            
                            # Convert to DataFrame with safer data extraction
                            chart_data = []
                            try:
                                for date_str, values in price_data.items():
                                    price = safe_get_price(price_data, date_str, "Close")
                                    if price > 0:  # Only add valid prices
                                        chart_data.append({
                                            "date": pd.to_datetime(date_str),
                                            "price": price
                                        })
                            except Exception as e:
                                logger.error(f"Error preparing chart data for {symbol}: {e}")
                            
                            df = pd.DataFrame(chart_data)
                            if not df.empty:
                                chart = alt.Chart(df).mark_line(color=color).encode(
                                    x='date',
                                    y='price',
                                    tooltip=['date', 'price']
                                ).properties(height=300)
                                st.altair_chart(chart, use_container_width=True)
                    
                    # Display NLP data if available
                    if nlp_data:
                        st.subheader("🔍 NLP Analysis of News")
                        
                        # Show news articles with their key insights
                        for j, article in enumerate(nlp_data[:3]):  # Show up to 3 articles
                            with st.expander(f"📰 Article {j+1}: {article.get('title', 'Untitled')}", expanded=False):
                                col1, col2 = st.columns([1, 1])
                                
                                with col1:
                                    st.markdown(f"**Title:** {article.get('title', 'No title')}")
                                    st.markdown(f"**Date:** {article.get('date', 'Unknown date')}")
                                    if 'url' in article:
                                        st.markdown(f"[Read original article]({article['url']})")
                                
                                with col2:
                                    # Display key insights
                                    if 'keywords' in article and article['keywords']:
                                        st.markdown("**Keywords:**")
                                        keywords_html = " ".join([f'<span style="background-color: {color}33; border-radius: 5px; padding: 2px 8px; margin: 2px; display: inline-block;">{kw}</span>' for kw in article['keywords'][:8]])
                                        st.markdown(f'<div style="line-height: 2.5;">{keywords_html}</div>', unsafe_allow_html=True)
                                
                                # Display key sentences
                                if 'key_sentences' in article and article['key_sentences']:
                                    st.markdown("**Key Information:**")
                                    st.markdown(f'<div style="background-color: #F0F2F6; padding: 10px; border-radius: 5px;">{article["key_sentences"]}</div>', unsafe_allow_html=True)
                                
                                # Display named entities if available
                                if 'named_entities' in article and article['named_entities']:
                                    st.markdown("**Named Entities:**")
                                    for entity_type, entities in article['named_entities'].items():
                                        if entities and entity_type in ['ORG', 'PERSON', 'GPE', 'DATE', 'MONEY', 'PERCENT']:
                                            st.markdown(f"**{entity_type}:** {', '.join(entities[:10])}")
                                
                                # Display article summary if available
                                if 'summary' in article and article['summary']:
                                    st.markdown("**AI Summary:**")
                                    st.markdown(f'<div style="background-color: #F0F2F6; padding: 10px; border-radius: 5px; border-left: 4px solid {color};">{article["summary"]}</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center;">
        <p>NLPStock Analyzer | Powered by Groq LLM | Streamlit UI</p>
        <p style="font-size: 12px; color: #666;">Last updated: April 2025</p>
    </div>
    """, 
    unsafe_allow_html=True) 