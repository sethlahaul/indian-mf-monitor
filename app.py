import streamlit as st

# App configuration - MUST be first Streamlit command
st.set_page_config(
    page_title="Indian Mutual Fund Analyzer",
    page_icon="📈",
    layout="wide"
)

import pandas as pd
from mftool import Mftool
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# Initialize the mftool object
@st.cache_resource
def get_mf_tool():
    return Mftool()

mf = get_mf_tool()

st.title("📈 Indian Mutual Fund Analyzer")
st.markdown("Analyze Indian Mutual Funds using real-time data")

# Sidebar for navigation
st.sidebar.title("Navigation")
option = st.sidebar.selectbox(
    "Choose an option:",
    ["Search Funds", "SIP Calculator", "SIP Goal Planner"]
)

if option == "Search Funds":
    st.header("🔍 Search Mutual Funds")
    
    # Get all scheme codes (this might take a moment)
    with st.spinner("Loading available funds..."):
        try:
            all_schemes = mf.get_scheme_codes()
            if all_schemes:
                scheme_names = list(all_schemes.values())
                scheme_codes = list(all_schemes.keys())
            else:
                st.error("Unable to fetch scheme data. Please try again later.")
                st.stop()
        except Exception as e:
            st.error(f"Error fetching schemes: {str(e)}")
            st.stop()
    
    # Fund selection dropdown
    selected_fund = st.selectbox(
        "Select a mutual fund:",
        options=[""] + scheme_names,  # Add empty option as default
        index=0,
        help="Choose a fund from the dropdown list"
    )
    
    if selected_fund:
        # Get scheme code for selected fund
        selected_code = None
        for code, name in all_schemes.items():
            if name == selected_fund:
                selected_code = code
                break
        
        if selected_code:
            st.write(f"**Selected Fund:** {selected_fund}")
            
            # Display fund details in organized way
            code, name = selected_code, selected_fund
            with st.expander(f"{name}", expanded=True):
                st.write(f"**Scheme Code:** {code}")
                
                # Get current NAV automatically
                try:
                    with st.spinner("Fetching fund data..."):
                        nav_data = mf.get_scheme_quote(code)
                        if nav_data:
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Current NAV", f"₹{nav_data.get('nav', 'N/A')}")
                            with col2:
                                st.metric("Last Updated", nav_data.get('last_updated', 'N/A'))
                            with col3:
                                st.metric("Scheme Code", code)
                        else:
                            st.error("NAV data not available")
                            
                        # Get historical data from fund inception
                        st.info("Complete historical data from fund inception.")
                        
                        # Try to get maximum historical data available
                        # Most funds have data going back several years, we'll try different ranges
                        historical_data = None
                        
                        # Try to get data from as far back as possible
                        # Start with 20 years ago and work backwards if needed
                        max_years_back = 20
                        end_date = datetime.now()
                        
                        for years_back in range(max_years_back, 0, -1):
                            try:
                                start_date = end_date - timedelta(days=365 * years_back)
                                historical_data = mf.get_scheme_historical_nav(
                                    code, 
                                    start_date.strftime('%d-%m-%Y'),
                                    end_date.strftime('%d-%m-%Y')
                                )
                                
                                if historical_data and 'data' in historical_data and historical_data['data']:
                                    break
                            except:
                                continue
                        
                        # If above approach doesn't work, try the scheme info to get inception date
                        if not historical_data or not historical_data.get('data'):
                            try:
                                # Try getting scheme info which might contain inception date
                                scheme_info = mf.get_scheme_details(code)
                                if scheme_info and 'scheme_start_date' in scheme_info:
                                    inception_date = datetime.strptime(scheme_info['scheme_start_date']['date'], '%d-%m-%Y')
                                    historical_data = mf.get_scheme_historical_nav(
                                        code,
                                        inception_date.strftime('%d-%m-%Y'),
                                        end_date.strftime('%d-%m-%Y')
                                    )
                            except:
                                # Fallback to 10 years if scheme info not available
                                start_date = end_date - timedelta(days=365 * 10)
                                historical_data = mf.get_scheme_historical_nav(
                                    code,
                                    start_date.strftime('%d-%m-%Y'),
                                    end_date.strftime('%d-%m-%Y')
                                )
                        
                        if historical_data and 'data' in historical_data and historical_data['data']:
                            df = pd.DataFrame(historical_data['data'])
                            df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
                            df['nav'] = pd.to_numeric(df['nav'])
                            df = df.sort_values('date')
                            
                            # Calculate fund age and inception details
                            inception_date = df['date'].iloc[0]
                            current_date = df['date'].iloc[-1]
                            fund_age_days = (current_date - inception_date).days
                            fund_age_years = fund_age_days / 365.25
                            
                            # Display fund inception information
                            st.subheader("📅 Fund Information")
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Inception Date", inception_date.strftime('%d-%m-%Y'))
                            with col2:
                                st.metric("Fund Age", f"{fund_age_years:.1f} years")
                            with col3:
                                st.metric("Data Points", len(df))
                            with col4:
                                st.metric("Last NAV Date", current_date.strftime('%d-%m-%Y'))
                            
                            # Create comprehensive performance chart
                            st.subheader(f"📈 Complete NAV Performance (Since Inception)")
                            
                            fig = px.line(df, x='date', y='nav', 
                                        title=f"NAV Trend Since Inception - {name}")
                            fig.update_layout(
                                xaxis_title="Date",
                                yaxis_title="NAV (₹)",
                                height=500,
                                showlegend=False
                            )
                            
                            # Add hover information
                            fig.update_traces(
                                mode='lines',
                                hovertemplate='<b>Date:</b> %{x}<br><b>NAV:</b> ₹%{y:.2f}<extra></extra>'
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Calculate comprehensive performance metrics
                            st.subheader("🎯 Performance Metrics")
                            
                            inception_nav = df['nav'].iloc[0]
                            current_nav = df['nav'].iloc[-1]
                            
                            # Total returns since inception
                            total_return = ((current_nav - inception_nav) / inception_nav) * 100
                            
                            # Annualized returns (CAGR)
                            cagr = (((current_nav / inception_nav) ** (1/fund_age_years)) - 1) * 100
                            
                            # Display key metrics
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Inception NAV", f"₹{inception_nav:.2f}")
                            with col2:
                                st.metric("Current NAV", f"₹{current_nav:.2f}")
                            with col3:
                                st.metric("Total Return", f"{total_return:.2f}%", 
                                        delta=f"{total_return:.2f}%")
                            with col4:
                                st.metric("CAGR", f"{cagr:.2f}%", 
                                        delta=f"{cagr:.2f}%")
                            
                            # Additional performance analysis
                            if len(df) > 365:
                                # Calculate various period returns
                                periods = []
                                returns_data = []
                                
                                # Calculate returns for different periods if data is available
                                time_periods = [
                                    (30, "1 Month"),
                                    (90, "3 Months"), 
                                    (180, "6 Months"),
                                    (365, "1 Year"),
                                    (730, "2 Years"),
                                    (1095, "3 Years"),
                                    (1825, "5 Years"),
                                    (2190, "6 Years"),
                                    (2555, "7 Years"),
                                    (2920, "8 Years"),
                                    (3285, "9 Years"),
                                    (3650, "10 Years"),
                                    (4015, "11 Years"),
                                    (4380, "12 Years"),
                                    (4745, "13 Years"),
                                    (5110, "14 Years"),
                                    (5475, "15 Years"),
                                    (5840, "16 Years"),
                                    (6205, "17 Years"),
                                    (6570, "18 Years"),
                                    (6935, "19 Years"),
                                    (7300, "20 Years"),
                                    (7665, "21 Years"),
                                    (8030, "22 Years"),
                                    (8395, "23 Years"),
                                    (8760, "24 Years"),
                                    (9125, "25 Years"),
                                    (9490, "26 Years"),
                                    (9855, "27 Years"),
                                    (10220, "28 Years"),
                                    (10585, "29 Years"),
                                    (10950, "30 Years"),
                                    (11315, "31 Years"),
                                    (11680, "32 Years"),
                                    (12045, "33 Years"),
                                    (12410, "34 Years"),
                                    (12775, "35 Years"),
                                    (13140, "36 Years"),
                                    (13505, "37 Years"),
                                    (13870, "38 Years"),
                                    (14235, "39 Years"),
                                    (14600, "40 Years")
                                ]
                                
                                for days, period_name in time_periods:
                                    if len(df) > days:
                                        old_nav = df['nav'].iloc[-days-1]
                                        period_return = ((current_nav - old_nav) / old_nav) * 100
                                        
                                        # Calculate annualized return for periods > 1 year
                                        if days >= 365:
                                            years = days / 365.25
                                            annualized_return = (((current_nav / old_nav) ** (1/years)) - 1) * 100
                                            returns_data.append({
                                                'Period': period_name,
                                                'Absolute Return': f"{period_return:.2f}%",
                                                'Annualized Return': f"{annualized_return:.2f}%"
                                            })
                                        else:
                                            returns_data.append({
                                                'Period': period_name,
                                                'Absolute Return': f"{period_return:.2f}%",
                                                'Annualized Return': 'N/A'
                                            })
                                
                                if returns_data:
                                    st.subheader("📊 Period-wise Returns")
                                    returns_df = pd.DataFrame(returns_data)
                                    st.dataframe(returns_df, use_container_width=True)
                                
                                # Risk metrics
                                st.subheader("⚠️ Risk Metrics")
                                
                                # Calculate daily returns for volatility
                                df['daily_return'] = df['nav'].pct_change()
                                
                                # Annual volatility
                                annual_volatility = df['daily_return'].std() * (252 ** 0.5) * 100
                                
                                # Max drawdown calculation
                                df['rolling_max'] = df['nav'].expanding().max()
                                df['drawdown'] = (df['nav'] - df['rolling_max']) / df['rolling_max']
                                max_drawdown = df['drawdown'].min() * 100
                                
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Annual Volatility", f"{annual_volatility:.2f}%")
                                with col2:
                                    st.metric("Max Drawdown", f"{max_drawdown:.2f}%")
                                with col3:
                                    if annual_volatility > 0:
                                        sharpe_approx = cagr / annual_volatility
                                        st.metric("Risk-Return Ratio", f"{sharpe_approx:.2f}")
                                    else:
                                        st.metric("Risk-Return Ratio", "N/A")
                        
                        else:
                            st.error("Historical data not available for this fund")
                            
                except Exception as e:
                    st.error(f"Error fetching fund data: {str(e)}")
                    st.error("Please try selecting a different fund or try again later.")
        else:
            st.error("Unable to find scheme code for selected fund")

elif option == "SIP Calculator":
    st.header("💰 SIP Calculator")
    st.markdown("Calculate the future value of your SIP investments and plan your financial goals")
    
    # Create two tabs for different calculators
    tab1, tab2 = st.tabs(["💸 SIP Future Value", "🎯 Target Amount Calculator"])
    
    with tab1:
        st.subheader("Calculate Future Value of SIP")
        st.markdown("See how much your regular SIP investments will grow over time")
        
        col1, col2 = st.columns(2)
        
        with col1:
            monthly_investment = st.number_input(
                "Monthly SIP Amount (₹)", 
                min_value=500, 
                max_value=1000000, 
                value=5000, 
                step=500,
                help="Enter the amount you want to invest every month"
            )
            
            annual_return = st.slider(
                "Expected Annual Return (%)", 
                min_value=1.0, 
                max_value=30.0, 
                value=12.0, 
                step=0.5,
                help="Expected annual return rate from your investment"
            )
            
            investment_years = st.slider(
                "Investment Period (Years)", 
                min_value=1, 
                max_value=40, 
                value=10, 
                step=1,
                help="How long do you plan to continue your SIP"
            )
        
        with col2:
            # Calculate SIP returns
            monthly_rate = annual_return / (12 * 100)
            total_months = investment_years * 12
            
            # SIP Future Value Formula: PMT * [((1 + r)^n - 1) / r] * (1 + r)
            if monthly_rate > 0:
                future_value = monthly_investment * (((1 + monthly_rate) ** total_months - 1) / monthly_rate) * (1 + monthly_rate)
            else:
                future_value = monthly_investment * total_months
            
            total_investment = monthly_investment * total_months
            wealth_gained = future_value - total_investment
            
            # Display results
            st.metric("Total Investment", f"₹{total_investment:,.0f}")
            st.metric("Future Value", f"₹{future_value:,.0f}")
            st.metric("Wealth Gained", f"₹{wealth_gained:,.0f}", 
                     delta=f"{(wealth_gained/total_investment)*100:.1f}%")
        
        # Visualization
        st.subheader("📊 Investment Growth Visualization")
        
        # Create year-wise breakdown
        years = list(range(1, investment_years + 1))
        investment_values = []
        future_values = []
        
        for year in years:
            months = year * 12
            invested = monthly_investment * months
            if monthly_rate > 0:
                fv = monthly_investment * (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)
            else:
                fv = invested
            
            investment_values.append(invested)
            future_values.append(fv)
        
        # Create DataFrame for plotting
        chart_df = pd.DataFrame({
            'Year': years,
            'Total Investment': investment_values,
            'Future Value': future_values
        })
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=chart_df['Year'], y=chart_df['Total Investment'], 
                                mode='lines+markers', name='Total Investment',
                                line=dict(color='#ff6b6b', width=3)))
        fig.add_trace(go.Scatter(x=chart_df['Year'], y=chart_df['Future Value'], 
                                mode='lines+markers', name='Future Value',
                                line=dict(color='#4ecdc4', width=3)))
        
        fig.update_layout(
            title=f"SIP Growth Projection - ₹{monthly_investment:,}/month at {annual_return}% annual return",
            xaxis_title="Years",
            yaxis_title="Amount (₹)",
            height=500,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Year-wise breakdown table
        with st.expander("Year-wise Breakdown"):
            chart_df['Wealth Gained'] = chart_df['Future Value'] - chart_df['Total Investment']
            chart_df['Total Investment'] = chart_df['Total Investment'].apply(lambda x: f"₹{x:,.0f}")
            chart_df['Future Value'] = chart_df['Future Value'].apply(lambda x: f"₹{x:,.0f}")
            chart_df['Wealth Gained'] = chart_df['Wealth Gained'].apply(lambda x: f"₹{x:,.0f}")
            st.dataframe(chart_df, use_container_width=True)
    
    with tab2:
        st.subheader("Target Amount Calculator")
        st.markdown("Calculate the monthly SIP needed to reach your financial goal")
        
        col1, col2 = st.columns(2)
        
        with col1:
            target_amount = st.number_input(
                "Target Amount (₹)", 
                min_value=100000, 
                max_value=100000000, 
                value=1000000, 
                step=100000,
                help="The amount you want to accumulate"
            )
            
            target_years = st.slider(
                "Time Period (Years)", 
                min_value=1, 
                max_value=40, 
                value=10, 
                step=1,
                help="Time available to reach your goal"
            )
            
            expected_return = st.slider(
                "Expected Annual Return (%)", 
                min_value=1.0, 
                max_value=30.0, 
                value=12.0, 
                step=0.5,
                help="Expected annual return from your investment"
            )
        
        with col2:
            # Calculate required SIP
            monthly_rate = expected_return / (12 * 100)
            total_months = target_years * 12
            
            # Required SIP Formula: Target Amount / [((1 + r)^n - 1) / r * (1 + r)]
            if monthly_rate > 0:
                required_sip = target_amount / ((((1 + monthly_rate) ** total_months - 1) / monthly_rate) * (1 + monthly_rate))
            else:
                required_sip = target_amount / total_months
            
            total_investment_needed = required_sip * total_months
            wealth_to_be_gained = target_amount - total_investment_needed
            
            # Display results
            st.metric("Required Monthly SIP", f"₹{required_sip:,.0f}")
            st.metric("Total Investment", f"₹{total_investment_needed:,.0f}")
            st.metric("Wealth to be Gained", f"₹{wealth_to_be_gained:,.0f}",
                     delta=f"{(wealth_to_be_gained/total_investment_needed)*100:.1f}%")
        
        # Goal scenarios
        st.subheader("🎯 Different Scenarios")
        
        scenarios_data = []
        return_rates = [8, 10, 12, 15, 18]
        
        for rate in return_rates:
            monthly_rate_scenario = rate / (12 * 100)
            if monthly_rate_scenario > 0:
                sip_needed = target_amount / ((((1 + monthly_rate_scenario) ** total_months - 1) / monthly_rate_scenario) * (1 + monthly_rate_scenario))
            else:
                sip_needed = target_amount / total_months
            
            scenarios_data.append({
                'Annual Return': f"{rate}%",
                'Required Monthly SIP': f"₹{sip_needed:,.0f}",
                'Total Investment': f"₹{sip_needed * total_months:,.0f}"
            })
        
        scenarios_df = pd.DataFrame(scenarios_data)
        st.dataframe(scenarios_df, use_container_width=True)

elif option == "SIP Goal Planner":
    st.header("🎯 SIP Goal Planner")
    st.markdown("Plan your SIPs for different life goals")
    
    # Predefined goals
    st.subheader("Common Financial Goals")
    
    goals = {
        "Child's Education": {"amount": 2000000, "years": 15, "return": 12},
        "Child's Marriage": {"amount": 1500000, "years": 20, "return": 12},
        "Retirement Planning": {"amount": 10000000, "years": 25, "return": 12},
        "Dream Home": {"amount": 5000000, "years": 10, "return": 12},
        "Dream Car": {"amount": 1000000, "years": 5, "return": 12},
        "Emergency Fund": {"amount": 500000, "years": 3, "return": 8},
        "Vacation Fund": {"amount": 300000, "years": 2, "return": 10}
    }
    
    selected_goals = st.multiselect(
        "Select your goals:",
        list(goals.keys()),
        default=["Child's Education", "Retirement Planning"],
        help="Choose the financial goals you want to plan for"
    )
    
    if selected_goals:
        st.subheader("📋 Your Goal Planning Summary")
        
        total_monthly_sip = 0
        goal_details = []
        
        for goal in selected_goals:
            goal_data = goals[goal]
            
            # Allow users to customize goal parameters
            with st.expander(f"Customize {goal}", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    custom_amount = st.number_input(
                        f"Target Amount for {goal} (₹)",
                        min_value=50000,
                        max_value=50000000,
                        value=goal_data["amount"],
                        step=50000,
                        key=f"amount_{goal}"
                    )
                with col2:
                    custom_years = st.slider(
                        f"Years to achieve {goal}",
                        min_value=1,
                        max_value=40,
                        value=goal_data["years"],
                        key=f"years_{goal}"
                    )
                with col3:
                    custom_return = st.slider(
                        f"Expected return for {goal} (%)",
                        min_value=6.0,
                        max_value=25.0,
                        value=float(goal_data["return"]),
                        step=0.5,
                        key=f"return_{goal}"
                    )
                
                # Update goal data with custom values
                goal_data = {
                    "amount": custom_amount,
                    "years": custom_years,
                    "return": custom_return
                }
            
            # Calculate required SIP for this goal
            monthly_rate = goal_data["return"] / (12 * 100)
            total_months = goal_data["years"] * 12
            
            if monthly_rate > 0:
                required_sip = goal_data["amount"] / ((((1 + monthly_rate) ** total_months - 1) / monthly_rate) * (1 + monthly_rate))
            else:
                required_sip = goal_data["amount"] / total_months
            
            total_monthly_sip += required_sip
            
            goal_details.append({
                'Goal': goal,
                'Target Amount': f"₹{goal_data['amount']:,}",
                'Time Period': f"{goal_data['years']} years",
                'Expected Return': f"{goal_data['return']}%",
                'Monthly SIP Required': f"₹{required_sip:,.0f}"
            })
        
        # Display goal summary
        goals_df = pd.DataFrame(goal_details)
        st.dataframe(goals_df, use_container_width=True)
        
        # Total summary
        st.subheader("💼 Total Investment Summary")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Monthly SIP Required", f"₹{total_monthly_sip:,.0f}")
        with col2:
            st.metric("Total Annual Investment", f"₹{total_monthly_sip * 12:,.0f}")
        with col3:
            total_target = sum([goals[goal]["amount"] for goal in selected_goals])
            st.metric("Combined Target Amount", f"₹{total_target:,}")
        
        # Investment allocation pie chart
        st.subheader("📊 SIP Allocation by Goals")
        
        sip_amounts = [float(detail['Monthly SIP Required'].replace('₹', '').replace(',', '')) 
                      for detail in goal_details]
        
        fig_pie = px.pie(
            values=sip_amounts,
            names=selected_goals,
            title="Monthly SIP Allocation"
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
        
        # Timeline visualization
        st.subheader("⏰ Goal Timeline")
        
        timeline_data = []
        for goal in selected_goals:
            goal_data = goals[goal] if goal in goals else goals[selected_goals[0]]  # Fallback
            timeline_data.append({
                'Goal': goal,
                'Years': goal_data['years'],
                'Target': goal_data['amount']
            })
        
        timeline_df = pd.DataFrame(timeline_data)
        timeline_df = timeline_df.sort_values('Years')
        
        fig_timeline = px.bar(
            timeline_df,
            x='Goal',
            y='Years',
            title="Goal Achievement Timeline",
            color='Target',
            color_continuous_scale='viridis'
        )
        fig_timeline.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_timeline, use_container_width=True)
    
    # SIP Tips
    st.subheader("💡 SIP Investment Tips")
    tips_col1, tips_col2 = st.columns(2)
    
    with tips_col1:
        st.info("""
        **Start Early**: The power of compounding works best over longer periods.
        
        **Stay Consistent**: Don't skip SIP installments, even during market volatility.
        
        **Increase Gradually**: Consider increasing your SIP amount by 10-15% annually.
        """)
    
    with tips_col2:
        st.info("""
        **Diversify**: Spread your investments across different fund categories.
        
        **Review Regularly**: Monitor fund performance and rebalance if needed.
        
        **Tax Planning**: Utilize ELSS funds for tax saving under Section 80C.
        """)

# Footer
st.markdown("---")
st.markdown("**Note:** This tool uses the mftool library to fetch real-time mutual fund data from AMFI. "
           "Data accuracy depends on the source API availability.")
st.markdown("⚠️ **Disclaimer:** This is for informational purposes only and should not be considered as investment advice.")