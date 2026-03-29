This dashboard suite transforms daily agricultural market data into actionable intelligence for farmers. Four interconnected dashboards answer the core questions every farmer needs:
Dashboard	Question	Decision
Today's Market	"What should I sell today?"	Immediate harvest decisions
Planning Calendar	"When should I sell?"	Harvest scheduling
Product Strategy	"What configuration should I pack?"	Packaging optimization
Market Intelligence	"Where is the market heading?"	Strategic planning


## Dashboard 1: Today's Market

`Answering: "What should I sell today?"`

### Purpose

Provides real-time market conditions to guide immediate selling decisions. Farmers can see at a glance which varieties are commanding premium prices, what containers to use, and whether today is a high-volume opportunity.

### Data Source

daily_market_snapshot - Aggregated daily market data at variety-container-grade level

### Visual Components

Component   |	What It Shows   |	Farmer Action
|------------|-------------------|----------------|
KPI Cards   |    Total Market Value, Volume, Active Varieties, Active Containers    |	Quick market overview
Price Alert | Card Premium variety (e.g., Granny Smith) with price vs market average    |	"SELL NOW" trigger
Top Varieties   | Bar Chart	5 highest-priced varieties today    |	Which to prioritize
Container Recommendation    |	Best container for today (Recommended, Consider, Avoid) |	Packaging choice
Volume Comparison   |	Today's volume vs 30-day average (Well Above, Above, Normal, Below, Well Below) |	Supply planning
Quick Actions   |	Pre-populated recommendations   |	One-click decisions

### Key Metrics Explained

Metric  |	Calculation |	Interpretation
|-------|----------------|-----------------|
avg_price_per_kg    |	Weighted average by volume  |	True market price, not simple average
price_rank_within_commodity |	Rank among all varieties (1=highest)    |	Quick premium identification
volume_vs_historical_pct    |	(Today - 30d avg) / 30d avg × 100   |	Market activity level
container_recommendation    |	Composite score (price + value - volatility)    |	Optimal packaging

### How to Use

- Check the date filter - ensure it's set to "Today"

- Review Price Alert - if highlighted, sell that variety immediately

- Scan Top Varieties - prioritize those with highest prices

- Choose container - use Recommended for best return

- Check volume comparison - adjust quantity based on demand

## Dashboard 2: Planning Calendar

Answering: "When should I sell?"

### Purpose

Identifies optimal selling times based on historical patterns. Helps farmers schedule harvests to align with premium price periods.

### Data Source

time_pattern_analysis - Aggregated patterns by day of week, week of month, and season

### Visual Components

Component   |	What It Shows   |	Farmer Action
|------------|-------------------|----------------|
Best Days to Sell   | Chart	Average price by day of week    |	Schedule harvest for premium days
Week of Month Analysis  |	Price patterns across weeks 1-4 |	Target week 2-3 for best prices
Seasonal Trends |	Average prices by season    |	Plan for summer vs winter harvests
Confidence Scores   |	Reliability of each pattern |	Trust high-confidence insights
Recommendation Panel    |	Dynamic text with optimal timing    |	Direct guidance

### Key Metrics Explained

Metric  |	Calculation |	Interpretation
|--------|---------------|-----------------|
avg_price   |	Weighted average for time slice |	Expected price for that period
price_rank  |	1 = best price within pattern type  |	Quick identification of best day/week/season
confidence_score    |	Based on sample size and volatility	|   High = trust pattern, Low = use caution
price_lower_bound/upper_bound   |	95% confidence interval	|   Expected price range

### How to Use

- Select commodity from dropdown (e.g., "apples")

- Identify best day - look for highest bar on day-of-week chart

- Plan harvest - if Tuesday is best, harvest Monday evening

- Target optimal week - aim for weeks 2-3 of the month

- Consider seasonality - summer typically yields highest prices

- Check confidence - only rely on patterns with "High" confidence

## Dashboard 3: Product Strategy

`Answering: "What configuration should I pack?"`

### Purpose

Optimizes product mix by identifying which combinations of variety, container, size, and grade perform best. Helps farmers maximize profit per container.

### Data Source

product_optimization - Historical analysis of product combinations

### Visual Components

Component |	What It Shows	| Farmer Action
|----------|-----------------|--------------|
Top Performers Table |	Best variety-container-size-grade combinations |	Focus on top-ranked products
Size Analysis |	Price comparison by size category   |	Choose optimal size for packing
Grade Comparison    |	Class 1 vs Class 2 price differential   |	Decide if premium grading is worth it
Container Economics	    |   Value per container by type |   Select most profitable packaging
Volume Trends   |	Growing vs declining demand |	Shift production to growing varieties
Optimization Score  |	Composite price-volume ranking |	Identify "sweet spot" products

### Key Metrics Explained
Metric  |	Calculation |	Interpretation
|--------|---------------|-----------------|
optimization_score  |	(price × log(volume)) / 1000    |	Balances profit and practicality
overall_rank    |	1 = best combination    |	Quick comparison across all products
volume_trend_pct    |	30-day vs previous 30-day   |	Growing (+), declining (-) demand
price_stability	    |   Low = stable, High = volatile   |	Risk assessment
market_share_percent    |	Product volume / total market   |	Product popularity

### How to Use

- **Review Top Performers** - focus on combinations with overall_rank ≤ 10

- **Check Size Analysis** - large sizes typically command premium prices

- **Evaluate Grade Premium** - if Class 1 price > Class 2 by 30%+, invest in grading

- **Compare Container Economics** - use containers with highest value per unit

- **Follow Volume Trends** - increase production of growing varieties

- **Check Optimization Score** - high score = good balance of price and volume


## Dashboard 4: Market Intelligence

Answering: "Where is the market heading?"

### Purpose

Provides strategic market intelligence for long-term planning. Helps farmers decide what to plant next season, whether to expand operations, and when to diversify.

### Data Source

market_trends_analysis - Daily market-level trends with rolling averages

### Visual Components

|Component| What It Shows	|   Farmer Action |
|-----------|---------------|-----------------|
Market Health Scorecard	 | 0-100 health score + condition (Booming/Growing/Stable/Slowing/Declining)	| Strategic direction
Market Trends Combo Chart |	Price (line) + Volume (bars) over time |	Visual trend analysis
Change Metrics |	YoY and WoW price/volume changes	| Growth/decline indicators
Opportunity & Risk Flags |	Hot opportunity / High risk alerts |	Immediate strategic signals
Volatility Chart |	Price stability over time	| Risk assessment
Strategic Recommendations |	Dynamic text panel |	Direct guidance

### Key Metrics Explained
Metric	| Calculation |	Interpretation
|--------|-----------|----------------|
market_health_score |	0-100 composite (stability + momentum + diversity + premium) |	Overall market health
price_change_yoy_pct |	(Current price - Same day last year) / Same day last year × 100	| Long-term price trend
volume_change_yoy_pct |	(Current volume - Same day last year) / Same day last year × 100 |	Demand trend
price_volatility |	30-day standard deviation	| Price stability (lower = more stable)
is_hot_opportunity	| Price rising AND volume surging	| "EXPAND NOW" signal
is_high_risk	| High volatility OR low health score	| "BE CAUTIOUS" signal

### How to Use

    Check Market Health Score:

        80-100:  Booming → Expand production

        60-80: Growing → Increase investment

        40-60:  Stable → Maintain current levels

        25-40:  Slowing → Reduce cautiously

        0-25:  Declining → Diversify

    Review Trend Chart:

        Price line up + Volume bars up = Strong market

        Price up + Volume down = Premium but shrinking market

        Price down + Volume up = Commoditization

        Both down = Market decline

    Monitor Change Metrics:

        YoY > 10% = Strong growth

        YoY < -5% = Potential trouble

        WoW > 5% = Recent acceleration

    Act on Flags:

        - Hot Opportunity = Bring MORE to market

        - High Risk = Reduce exposure, diversify

    Follow Recommendations:

        Strategic actions update dynamically based on data

## Dashboard Navigation

The four dashboards are designed to be used in sequence:
text


            FARMER DECISION FLOW                    
                                                          
Today's Market    →    What to sell TOMMOROW                
                                                                
Planning Calendar  →   When to schedule HARVEST               
                                                                
Product Strategy    →   How to PACK for profit                
                                                                
Market Intelligence   →    Where to INVEST next season             



## Color Guide
Color	Meaning	Usage
- Green	Positive, Good, Recommended	Upward trends, high health score, Recommended
- Yellow/Gold	Caution, Moderate	Moderate trends, consider, premium indicator
- Red	Warning, Negative, Avoid	Downward trends, high risk, Avoid
- Orange	Action needed	Shortages, opportunities
- Gray	Neutral, Stable	Normal levels, stable trends

## Mobile Usage Tips

    Landscape orientation recommended for best view

    Pinch to zoom on charts for detail

    Use filters to focus on specific commodities

    Quick actions work as one-tap decisions

## Data Freshness

|**Dashboard** |	**Update Frequency** | **Last Data Point**  |
|---------------|-------------------------|----------------------|
Today's Market |	Daily, 3:00 PM	| Current date|
Planning Calendar |	Weekly	| Last 90 days |
Product Strategy |	Weekly	| Last 90 days |
Market Intelligence |	Daily	| Last 365 days |

## Pro Tips for Farmers

- Start with Today's Market each morning before harvest

- Use Planning Calendar to schedule your week

- Review Product Strategy monthly to optimize packaging

- Check Market Intelligence quarterly for strategic planning

- Follow the recommendations - they're based on real market data

- Pay attention to confidence scores - only act on high-confidence patterns

## Support

For questions about the data or dashboard:

- Data freshness issues: Check the footer for last update timestamp

- Missing data: "Insufficient Data" appears when <30 days of history

- Technical issues: Contact `musaqwabe@gmail.com`

`Built with dbt, BigQuery, and Looker Studio | Data updated daily | Questions? Feedback?` 
