"""
Single source of the financial explanations shown in the app.

Every metric, chart and concept has an entry with an anchor on the
Methodology page. The pages link to `/methodology#<anchor>`; the Methodology
page renders the same entries, so a definition is written once.

Entry fields
- labels:   the labels used in the UI that point to this entry
- meaning:  what it tells an investor (first sentence = short tooltip)
- computed: how the app computes it
- reading:  how to interpret it, rules of thumb, pitfalls
"""

from __future__ import annotations

METHODOLOGY_PATH = "/methodology"

SECTIONS = [
    {
        "title": "Data",
        "anchor": "data",
        "entries": [
            {
                "anchor": "price-vs-total-return",
                "title": "Price index vs total-return index",
                "labels": ["Price index"],
                "meaning": (
                    "A price index only follows the prices of its components; a total-return index also adds back "
                    "the dividends (or coupons), as if they were reinvested. An investor in a fund or an ETF receives "
                    "those dividends, so the total-return version is what you actually earn."
                ),
                "computed": (
                    "The app uses Yahoo *adjusted* prices: for ETFs, funds and shares they include dividends. Yahoo "
                    "indices, however, are mostly price indices (^GSPC, ^STOXX50E, ^SSMI, ^FTSE, MSCI '-STRD'…). "
                    "An index is flagged as a price index unless its name says total/net return or performance "
                    "(e.g. ^SP500TR, the DAX)."
                ),
                "reading": (
                    "**If an instrument is a price index:** its returns are too low by roughly its dividend yield, "
                    "typically 1–3% a year for equities, which compounds to 10–35% of missing performance over ten "
                    "years. Sharpe, Sortino, Calmar and alpha are understated; volatility, correlation and the depth "
                    "of drawdowns are almost unchanged, but recoveries look slower. In a backtest its contribution is "
                    "understated and, when weights drift, its weight shrinks faster than it would in reality. An "
                    "index cannot be bought: a tracker earns the dividends but pays fees.\n\n"
                    "**If a benchmark is a price index:** the instrument (dividends included) gets a free head start "
                    "of about the dividend yield every year. Excess return, information ratio, alpha and up-capture "
                    "look better than they are; tracking error, beta and correlation are barely affected.\n\n"
                    "**If both are price indices:** the comparison between them is fair, but both understate what an "
                    "investor earns.\n\n"
                    "**Fix:** use a total-return ticker when Yahoo has one (for example ^SP500TR for the S&P 500) or "
                    "an accumulating ETF that tracks the index."
                ),
            },
            {
                "anchor": "currency-conversion",
                "title": "Currency conversion",
                "labels": ["Currency"],
                "meaning": (
                    "All prices are expressed in the base currency you choose, so every result includes the effect "
                    "of exchange rates, as it would for an investor in that currency."
                ),
                "computed": (
                    "Daily prices are multiplied by the daily Yahoo FX rate (crossed through USD when no direct pair "
                    "exists). Prices quoted in pence or cents (GBp, ZAc, ILA) are divided by 100. Yahoo FX history "
                    "starts around 2003, so older history of a foreign-currency instrument is dropped."
                ),
                "reading": (
                    "A US equity ETF seen in CHF combines the US market and the USD/CHF move. The trading currency of "
                    "a listing is not its currency exposure: a currency-hedged share class has its own ISIN."
                ),
            },
            {
                "anchor": "weekly-data",
                "title": "Weekly data and horizons",
                "labels": ["Returns across horizons", "Horizon"],
                "meaning": (
                    "All statistics use weekly prices (Friday close), which smooth out day-to-day noise and "
                    "differences in market holidays between countries."
                ),
                "computed": (
                    "Daily base-currency prices are resampled to the last price of each week ending Friday; an "
                    "unfinished current week is left out. Horizons: YTD, 1, 3, 5, 10 years and since inception. A "
                    "horizon is shown only when the instrument covers it entirely."
                ),
                "reading": (
                    "Under one year returns are cumulative (what you gained over the period). From one year on they "
                    "are annualised, so periods of different length can be compared."
                ),
            },
        ],
    },
    {
        "title": "Performance",
        "anchor": "performance",
        "entries": [
            {
                "anchor": "cumulative-return",
                "title": "Cumulative return",
                "labels": ["Cumulative return", "Return (cumulative)", "Excess return (cum.)"],
                "meaning": "The total gain or loss over the whole period, dividends included.",
                "computed": "Final price / first price − 1.",
                "reading": (
                    "+50% means 100 became 150. It is not comparable across periods of different length; use the "
                    "annualised return for that."
                ),
            },
            {
                "anchor": "annualised-return",
                "title": "Annualised return",
                "labels": ["Annualised return", "Return p.a.", "Excess return (ann.)"],
                "meaning": (
                    "The constant yearly return that would have produced the same final result: the average speed "
                    "at which money grew."
                ),
                "computed": "(final price / first price)^(365 / number of days) − 1, i.e. a geometric (compounded) average.",
                "reading": (
                    "Compare it with inflation and with a risk-free deposit. A higher return usually comes with more "
                    "risk, which is why the ratios below divide return by a measure of risk."
                ),
            },
            {
                "anchor": "best-worst-week",
                "title": "Best week, worst week, positive weeks",
                "labels": ["Best week", "Worst week", "Positive weeks"],
                "meaning": "The extremes of weekly performance and how often a week ended with a gain.",
                "computed": "Highest and lowest weekly return; share of weeks with a return above zero.",
                "reading": (
                    "The worst week shows what a bad week has felt like. Even good long-term investments often have "
                    "only 55–60% positive weeks: being down in a given week is normal."
                ),
            },
            {
                "anchor": "calendar-years",
                "title": "Calendar-year returns",
                "labels": ["Calendar years"],
                "meaning": "The return of each calendar year, as it would appear on a yearly statement.",
                "computed": "Last price of the year / last price of the previous year − 1. First and last years are partial.",
                "reading": "Shows how irregular returns are: a good average can hide several negative years.",
            },
            {
                "anchor": "rolling-return",
                "title": "Rolling 52-week return",
                "labels": ["Rolling return"],
                "meaning": "The return of the previous twelve months, recomputed every week.",
                "computed": "Price / price 52 weeks earlier − 1, for every week.",
                "reading": (
                    "It answers 'what if I had invested exactly one year before this date?'. The lowest point is the "
                    "worst one-year experience in the history."
                ),
            },
            {
                "anchor": "relative-performance",
                "title": "Relative performance",
                "labels": ["Relative performance"],
                "meaning": "Whether the instrument (or portfolio) is pulling ahead of its benchmark or falling behind.",
                "computed": "Instrument price / benchmark price, rebased to 100 at the start.",
                "reading": (
                    "A rising line means outperformance over that period, a falling line underperformance. Above 100 "
                    "at the end = ahead of the benchmark since the start."
                ),
            },
        ],
    },
    {
        "title": "Risk",
        "anchor": "risk",
        "entries": [
            {
                "anchor": "volatility",
                "title": "Volatility",
                "labels": ["Volatility (ann.)", "Volatility", "Rolling volatility"],
                "meaning": (
                    "How much returns swing around their average: the most common measure of risk. Higher volatility "
                    "means a bumpier ride and a wider range of possible outcomes."
                ),
                "computed": "Standard deviation of weekly returns × √52 (annualised).",
                "reading": (
                    "Rough orders of magnitude: bonds 3–7%, balanced portfolios 7–12%, equity markets 15–20%, single "
                    "stocks or emerging markets 20–35%. In a normal year, a return within ±1 volatility of the "
                    "average is common; ±2 volatilities happens about once every 20 years (more often in reality, "
                    "because markets have fat tails)."
                ),
            },
            {
                "anchor": "bootstrap-volatility",
                "title": "Bootstrap volatility (median and 5%–95% range)",
                "labels": ["Bootstrap vol (median)", "Bootstrap vol 5%", "Bootstrap vol 95%"],
                "meaning": (
                    "How precisely volatility is known. History is only one sample of what could have happened; "
                    "the bootstrap shows the range of volatilities consistent with that history."
                ),
                "computed": (
                    "Weekly returns are reshuffled 1,000 times in blocks of about 4 weeks (stationary bootstrap, which "
                    "keeps calm and stressed weeks together) and volatility is recomputed each time. The median and "
                    "the 5th–95th percentiles are reported."
                ),
                "reading": (
                    "A narrow range (e.g. 15–17%) means the estimate is reliable; a wide one (e.g. 10–25%) means short "
                    "or unstable history, so treat every risk number with caution."
                ),
            },
            {
                "anchor": "downside-deviation",
                "title": "Downside deviation",
                "labels": ["Downside deviation"],
                "meaning": "Volatility that only counts bad weeks, i.e. weeks below the risk-free rate.",
                "computed": "Root-mean-square of weekly returns below the risk-free rate (others count as zero) × √52.",
                "reading": (
                    "Investors mind losses more than gains. If downside deviation is much lower than volatility, much "
                    "of the volatility comes from upside moves."
                ),
            },
            {
                "anchor": "max-drawdown",
                "title": "Maximum drawdown and recovery",
                "labels": ["Max drawdown", "Max drawdown trough", "Recovery (weeks)", "Drawdown"],
                "meaning": (
                    "The largest fall from a previous peak: the worst loss an investor who bought at the top would "
                    "have suffered before prices recovered."
                ),
                "computed": (
                    "For each week, price / highest price so far − 1; the maximum drawdown is the deepest value. "
                    "Trough = date of the low point; recovery = weeks from the trough until the previous peak is "
                    "regained ('–' if not yet recovered)."
                ),
                "reading": (
                    "A 50% fall needs a +100% gain to recover. Ask yourself whether you would have stayed invested "
                    "through that loss and that recovery time: it is often a better test of risk tolerance than "
                    "volatility."
                ),
            },
            {
                "anchor": "var-es-historical",
                "title": "Value at Risk and Expected Shortfall (historical, 1 week)",
                "labels": ["VaR (1w, hist.)", "ES (1w, hist.)"],
                "meaning": (
                    "VaR: a loss that is not exceeded in most weeks (95% by default). Expected Shortfall (ES): the "
                    "average loss in the remaining worst weeks — 'when it goes badly, how badly on average?'."
                ),
                "computed": (
                    "From the past weekly returns: VaR = 5th percentile of returns (as a loss); ES = average of the "
                    "returns below that percentile."
                ),
                "reading": (
                    "VaR 95% of 3% means about one week in twenty loses more than 3%. ES is always larger than VaR "
                    "and is the better measure of tail risk, because it looks at how deep the bad weeks go."
                ),
            },
            {
                "anchor": "var-es-garch",
                "title": "Forward-looking VaR and ES (GARCH Monte Carlo)",
                "labels": ["Forward-looking risk", "VaR", "ES"],
                "meaning": (
                    "Tail risk for the next week, month and year given today's market conditions, rather than the "
                    "average of the past."
                ),
                "computed": (
                    "A GARCH(1,1) model with Student-t shocks is fitted to weekly log returns. It captures volatility "
                    "clustering (turbulent weeks tend to follow turbulent weeks) and fat tails. Starting from today's "
                    "estimated volatility, 10,000 future paths are simulated with Student-t draws; VaR and ES are "
                    "read from the simulated 1-week, 1-month and 1-year returns. With less than two years of data, "
                    "past returns are resampled instead."
                ),
                "reading": (
                    "When markets are stressed, today's volatility is above its long-run level and these numbers rise "
                    "above the historical ones; in calm markets they are lower. 'Persistence' close to 1 means shocks "
                    "fade slowly; a low ν (degrees of freedom) means fat tails."
                ),
            },
            {
                "anchor": "skewness-kurtosis",
                "title": "Skewness and excess kurtosis",
                "labels": ["Skewness", "Excess kurtosis"],
                "meaning": (
                    "The shape of the return distribution. Negative skewness: large losses are more frequent than "
                    "large gains. Positive excess kurtosis: extreme weeks (both ways) happen more often than a normal "
                    "bell curve predicts — 'fat tails'."
                ),
                "computed": "Third and fourth standardised moments of weekly returns (kurtosis minus 3).",
                "reading": (
                    "Equity markets typically show negative skewness and kurtosis well above 0. Combined, they mean "
                    "volatility alone understates the risk of a crash: look at drawdown and ES too."
                ),
            },
        ],
    },
    {
        "title": "Risk-adjusted ratios",
        "anchor": "ratios",
        "entries": [
            {
                "anchor": "sharpe-ratio",
                "title": "Sharpe ratio",
                "labels": ["Sharpe ratio"],
                "meaning": "Return earned above a risk-free deposit per unit of volatility: the reward for each unit of risk taken.",
                "computed": "(annualised return − risk-free rate) / volatility.",
                "reading": (
                    "Below 0: a deposit did better. 0.3–0.5 is typical of a broad equity market over long periods; "
                    "above 1 is rare and often does not last. Only compare Sharpe ratios over the same period."
                ),
            },
            {
                "anchor": "sortino-ratio",
                "title": "Sortino ratio",
                "labels": ["Sortino ratio"],
                "meaning": "Like the Sharpe ratio, but only penalises downside volatility.",
                "computed": "(annualised return − risk-free rate) / downside deviation.",
                "reading": "Higher is better. It favours investments whose volatility comes mostly from gains.",
            },
            {
                "anchor": "calmar-ratio",
                "title": "Calmar ratio",
                "labels": ["Calmar ratio"],
                "meaning": "Annual return per unit of the worst loss suffered.",
                "computed": "Annualised return / maximum drawdown.",
                "reading": (
                    "0.5 means it takes about two years of average returns to make up the worst drawdown. Sensitive "
                    "to a single crisis in the period."
                ),
            },
        ],
    },
    {
        "title": "Comparison with the benchmark",
        "anchor": "relative",
        "entries": [
            {
                "anchor": "tracking-error",
                "title": "Tracking error",
                "labels": ["Tracking error"],
                "meaning": "How far the instrument's returns stray from the benchmark's: the volatility of the difference.",
                "computed": "Standard deviation of (weekly instrument return − weekly benchmark return) × √52.",
                "reading": (
                    "Below 1%: an index tracker. 2–6%: an active fund staying close to its benchmark. Above 6%: a very "
                    "different investment — the benchmark may not be the right yardstick."
                ),
            },
            {
                "anchor": "information-ratio",
                "title": "Information ratio",
                "labels": ["Information ratio"],
                "meaning": "Excess return over the benchmark per unit of tracking error: how consistently the instrument beats it.",
                "computed": "(annualised return − benchmark annualised return) / tracking error.",
                "reading": (
                    "Above 0.5 is good and above 1 excellent for an active manager over several years. Beware of a "
                    "price-index benchmark, which inflates it."
                ),
            },
            {
                "anchor": "beta",
                "title": "Beta",
                "labels": ["Beta"],
                "meaning": "Sensitivity to the benchmark: how much the instrument tends to move when the benchmark moves by 1%.",
                "computed": "Covariance of weekly returns with the benchmark / variance of the benchmark.",
                "reading": "1 = moves with the benchmark; 1.2 = amplifies moves by 20%; 0.5 = half as sensitive (defensive).",
            },
            {
                "anchor": "alpha",
                "title": "Alpha (Jensen)",
                "labels": ["Alpha (Jensen, ann.)"],
                "meaning": "The part of the return not explained by exposure to the benchmark: value added (or lost) after accounting for beta.",
                "computed": "(return − risk-free) − beta × (benchmark return − risk-free), annualised.",
                "reading": "Positive alpha = outperformance beyond what the market exposure alone would deliver.",
            },
            {
                "anchor": "correlation",
                "title": "Correlation",
                "labels": ["Correlation"],
                "meaning": "How closely two sets of returns move together, from −1 (opposite) to +1 (in lockstep).",
                "computed": "Pearson correlation of weekly returns.",
                "reading": (
                    "Above 0.9: almost the same exposure. Around 0: independent. Negative: tends to rise when the "
                    "other falls — the most valuable property for diversification."
                ),
            },
            {
                "anchor": "capture-ratios",
                "title": "Up capture and down capture",
                "labels": ["Up capture", "Down capture"],
                "meaning": "How much of the benchmark's rises and falls the instrument has captured.",
                "computed": (
                    "Average instrument return in weeks when the benchmark rose (fell) / average benchmark return in "
                    "those weeks."
                ),
                "reading": (
                    "Ideal: up capture above 100% and down capture below 100%. Down capture of 80% means the instrument "
                    "lost on average only 80% of what the benchmark lost in bad weeks."
                ),
            },
            {
                "anchor": "weeks-outperforming",
                "title": "Weeks outperforming",
                "labels": ["Weeks outperforming"],
                "meaning": "The share of weeks in which the instrument did better than its benchmark.",
                "computed": "Count of weeks with instrument return > benchmark return / number of weeks.",
                "reading": "Around 50% is normal; consistent outperformers show 55%+ over long periods.",
            },
        ],
    },
    {
        "title": "Backtest",
        "anchor": "backtest",
        "entries": [
            {
                "anchor": "rebalancing",
                "title": "Drift vs rebalancing",
                "labels": ["Rebalancing"],
                "meaning": (
                    "Drift (buy and hold): positions are never traded, so winners grow into a larger share of the "
                    "portfolio. Rebalancing: positions are brought back to the target weights at a regular interval."
                ),
                "computed": (
                    "Rebalancing happens at the last weekly date of each period (week, month, quarter, half-year, "
                    "year). Transaction costs are charged on the amount traded."
                ),
                "reading": (
                    "Rebalancing keeps the risk profile you chose and systematically sells high / buys low, at the "
                    "cost of trading. Drifting lets the best performers dominate, which raises concentration risk "
                    "over time."
                ),
            },
            {
                "anchor": "late-entry",
                "title": "Instruments without data at the start",
                "labels": ["Late entry"],
                "meaning": "When the backtest starts before an instrument existed, that instrument cannot be held yet.",
                "computed": (
                    "Until its first price, it is left out and the other target weights are scaled up to 100%. When it "
                    "starts it is bought: by selling the others in proportion (drift) or by a rebalance. The composite "
                    "benchmark leaves out that instrument's benchmark over the same period."
                ),
                "reading": "The early years therefore describe a different, smaller portfolio than the one you entered.",
            },
            {
                "anchor": "composite-benchmark",
                "title": "Composite benchmark",
                "labels": ["Benchmark"],
                "meaning": "The same allocation invested in each instrument's benchmark: what a passive version of your portfolio would have done.",
                "computed": (
                    "Same target weights, same rebalancing rule and same inclusion dates as the portfolio, with no "
                    "fees. An instrument without a benchmark (or before its benchmark has data) keeps its own return, "
                    "so it adds no active return."
                ),
                "reading": (
                    "The gap with the portfolio measures the value added (or lost) by the instruments chosen. To "
                    "analyse the portfolio on its own, switch off 'Compare with benchmarks' on the Portfolio page."
                ),
            },
            {
                "anchor": "fees",
                "title": "Fees and turnover",
                "labels": ["Annualised turnover", "Total fees paid (% of start)", "Number of rebalances",
                           "Management fee", "Transaction cost"],
                "meaning": "The cost of running the portfolio.",
                "computed": (
                    "Management fee: annual %, charged weekly on the portfolio value (fund and ETF fees are already "
                    "inside Yahoo prices). Transaction cost: bps × the sum of absolute weight changes at each "
                    "rebalance or entry. Turnover: the share of the portfolio traded per year."
                ),
                "reading": (
                    "A 1% yearly fee costs about 10% of final wealth over ten years. Frequent rebalancing with high "
                    "transaction costs can cancel its benefit."
                ),
            },
            {
                "anchor": "attribution",
                "title": "Return attribution",
                "labels": ["Return attribution"],
                "meaning": "Which lines made (or lost) the money.",
                "computed": (
                    "For each week: portfolio value × the line's weight × the line's return, summed over time and "
                    "expressed in % of the starting value. Lines plus fees add up exactly to the cumulative return."
                ),
                "reading": "A line can have a large weight but a small contribution, or the reverse.",
            },
            {
                "anchor": "weights-over-time",
                "title": "Weights over time",
                "labels": ["Allocation over time"],
                "meaning": "How the share of each instrument in the portfolio evolved.",
                "computed": "Weights after each week's market moves and trades.",
                "reading": "With drift, compare the latest weights with your targets to see how far the portfolio moved.",
            },
        ],
    },
    {
        "title": "Correlation and diversification",
        "anchor": "diversification",
        "entries": [
            {
                "anchor": "ledoit-wolf",
                "title": "Correlation matrix (Ledoit-Wolf)",
                "labels": ["Correlation matrix", "Correlation and diversification"],
                "meaning": "How each pair of instruments moves together; low or negative correlations are what make diversification work.",
                "computed": (
                    "A plain historical covariance is noisy when there are many instruments and few weeks. "
                    "Ledoit-Wolf shrinks it towards a simple structure by the statistically optimal amount (the "
                    "shrinkage intensity shown); correlations are derived from it. Only weeks where every line has a "
                    "price are used."
                ),
                "reading": (
                    "Red cells (close to +1) are instruments that will tend to fall together. Correlations rise in "
                    "crises, so diversification is usually weaker exactly when it is needed."
                ),
            },
            {
                "anchor": "portfolio-volatility",
                "title": "Portfolio volatility and weighted average volatility",
                "labels": ["Portfolio volatility", "Weighted avg. volatility"],
                "meaning": (
                    "Portfolio volatility is the risk of the whole; the weighted average volatility is what the risk "
                    "would be if all lines moved perfectly together."
                ),
                "computed": "√(wᵀ Σ w) with the Ledoit-Wolf covariance Σ; weighted average = Σ wᵢ σᵢ.",
                "reading": "The gap between the two is the risk removed by diversification.",
            },
            {
                "anchor": "diversification-ratio",
                "title": "Diversification ratio",
                "labels": ["Diversification ratio"],
                "meaning": "How much diversification reduces risk.",
                "computed": "Weighted average volatility / portfolio volatility.",
                "reading": "1 = no benefit (one line, or lines moving in lockstep). 1.3 means risk is about 23% lower than without diversification.",
            },
            {
                "anchor": "effective-bets",
                "title": "Effective number of bets and of holdings",
                "labels": ["Effective nb of bets", "Effective nb of holdings"],
                "meaning": (
                    "How many truly independent sources of risk the portfolio holds (bets), and how many equally "
                    "weighted lines the weights are equivalent to (holdings)."
                ),
                "computed": (
                    "Bets (Meucci): risk is split across uncorrelated factors (principal components); the measure is "
                    "exp(entropy) of the factor risk shares. Holdings: 1 / Σ weight²."
                ),
                "reading": (
                    "Ten lines but 1.5 bets means the portfolio is essentially one risk (e.g. equities) in several "
                    "wrappers."
                ),
            },
            {
                "anchor": "average-correlation",
                "title": "Average correlation",
                "labels": ["Avg. correlation", "Avg. pairwise correlation"],
                "meaning": "The typical correlation between two lines of the portfolio, weighted by their size.",
                "computed": "Weight-weighted average of the off-diagonal Ledoit-Wolf correlations.",
                "reading": "Above 0.7 the lines behave much alike; below 0.3 they diversify each other well.",
            },
            {
                "anchor": "risk-contribution",
                "title": "Risk contribution",
                "labels": ["Risk contribution", "Weight vs share of portfolio risk"],
                "meaning": "The share of the portfolio's ups and downs that comes from each line.",
                "computed": "Euler decomposition: wᵢ × (Σw)ᵢ / portfolio variance; the shares add up to 100%.",
                "reading": (
                    "A 20% equity line can carry 60% of the risk in a stock/bond portfolio. If one line's share of "
                    "risk is far above its weight, it is the one driving results."
                ),
            },
        ],
    },
    {
        "title": "Forecast",
        "anchor": "forecast",
        "entries": [
            {
                "anchor": "monte-carlo",
                "title": "Monte Carlo simulation",
                "labels": ["Projected wealth", "Number of simulations", "Student-t"],
                "meaning": "Thousands of possible futures, to see the range of outcomes rather than a single forecast.",
                "computed": (
                    "Weekly returns are drawn from a multivariate Student-t distribution (fat tails) with the "
                    "Ledoit-Wolf volatilities and correlations; the degrees of freedom ν are estimated from history "
                    "(adjustable under Advanced). Each path applies your rebalancing rule, fees and cash flows."
                ),
                "reading": (
                    "The shaded bands contain 50% (dark) and 90% (light) of the simulated paths. Outcomes outside the "
                    "light band are possible: one path in ten ends outside it."
                ),
            },
            {
                "anchor": "expected-return",
                "title": "Expected return (your input)",
                "labels": ["Expected return % p.a."],
                "meaning": "What you assume each instrument will earn per year in the base currency, dividends included.",
                "computed": "It sets each instrument's median yearly growth in the simulation; risk comes from history.",
                "reading": (
                    "Past returns are shown as a reference only — they are a poor forecast. Typical long-run "
                    "assumptions: cash ≈ risk-free rate, bonds ≈ their yield, equities ≈ bonds + 3–5%."
                ),
            },
            {
                "anchor": "cash-flows",
                "title": "Cash flow plan",
                "labels": ["Cash flow plan", "Regular monthly investment"],
                "meaning": "Planned contributions (+) and withdrawals (−), e.g. a monthly savings plan or retirement income.",
                "computed": (
                    "The regular monthly investment adds the same amount every month for the chosen number of "
                    "years (negative = monthly withdrawal), growing by the yearly increase. Other flows can be "
                    "one-off, monthly, quarterly or annual, optionally growing each year (indexation). Each payment is "
                    "booked on the first simulated Friday on or after its date. "
                    "Contributions are invested at target weights (current weights when drifting); withdrawals are "
                    "taken pro rata."
                ),
                "reading": (
                    "Investing monthly spreads purchases over time (dollar-cost averaging): you buy more units when "
                    "prices are low, which smooths the entry price but does not remove market risk. Withdrawals early "
                    "in a bad market do lasting damage (sequence risk): watch the chance of running out."
                ),
            },
            {
                "anchor": "final-wealth",
                "title": "Final wealth (median, percentiles, mean)",
                "labels": ["Median final wealth", "Median terminal wealth", "Mean terminal wealth", "5th percentile",
                           "95th percentile", "Net amount invested"],
                "meaning": "The distribution of the portfolio value at the end of the horizon.",
                "computed": (
                    "Median: half of the simulations end above it. 5th / 95th percentile: 1 in 20 ends below / above. "
                    "Net amount invested: initial amount + contributions − withdrawals."
                ),
                "reading": (
                    "Plan on the median, prepare for the 5th percentile. The mean is above the median because a few "
                    "very good paths pull it up."
                ),
            },
            {
                "anchor": "forecast-probabilities",
                "title": "Probabilities: target, loss, running out",
                "labels": ["Chance of reaching target", "Chance of ending below invested", "Chance of running out",
                           "P(reaching target)", "P(ending below amount invested)", "P(depletion)"],
                "meaning": "The share of simulated futures in which each event happens.",
                "computed": (
                    "Target: final wealth ≥ target. Below invested: final wealth < net amount invested. Running out: "
                    "the portfolio reaches zero at any point because of withdrawals."
                ),
                "reading": "A 10% chance of running out means one future in ten where the plan fails — usually too high for retirement income.",
            },
            {
                "anchor": "forecast-return-risk",
                "title": "Median return and drawdowns in the forecast",
                "labels": ["Median return p.a.", "Median annualised return (TWR)", "Median max drawdown",
                           "Max drawdown (95th pct)", "Expected shortfall (worst 5%)"],
                "meaning": "The typical yearly return and the losses to expect along the way.",
                "computed": (
                    "Time-weighted return: cash flows excluded, fees included. Drawdowns are measured on that "
                    "time-weighted path. Expected shortfall: average final wealth of the worst 5% of simulations."
                ),
                "reading": "Even with a good median, the 95th-percentile drawdown shows the fall you should be ready to sit through.",
            },
            {
                "anchor": "real-terms",
                "title": "Today's money (inflation-adjusted)",
                "labels": ["Inflation", "Show in today's money"],
                "meaning": "Future amounts expressed in today's purchasing power.",
                "computed": "Each value is divided by (1 + inflation)^years.",
                "reading": "With 2% inflation, 100'000 in 20 years buys what about 67'000 buys today.",
            },
        ],
    },
]

# ── lookups ──────────────────────────────────────────────────────────────

_BY_LABEL: dict[str, dict] = {}
_BY_ANCHOR: dict[str, dict] = {}
for _section in SECTIONS:
    _BY_ANCHOR[_section["anchor"]] = {"anchor": _section["anchor"], "title": _section["title"], "meaning": ""}
    for _e in _section["entries"]:
        _BY_ANCHOR[_e["anchor"]] = _e
        for _label in _e["labels"]:
            _BY_LABEL[_label.lower()] = _e


def entry(key: str) -> dict | None:
    """Find an entry by UI label (case-insensitive) or by anchor."""
    if key is None:
        return None
    return _BY_LABEL.get(str(key).lower()) or _BY_ANCHOR.get(str(key))


def url(key: str) -> str | None:
    e = entry(key)
    return f"{METHODOLOGY_PATH}#{e['anchor']}" if e else None


def short(key: str) -> str:
    e = entry(key)
    if not e or not e["meaning"]:
        return ""
    first = e["meaning"].split(". ")[0].rstrip(".")
    return first + "."


def help_text(key: str) -> str | None:
    """Tooltip text: one-sentence explanation + link to the full entry."""
    e = entry(key)
    if not e or not e["meaning"]:
        return None
    return f"{short(key)}\n\n[What it means and how to read it ↗]({url(key)})"
