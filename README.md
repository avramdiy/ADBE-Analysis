 # TRG Week 44

 ## $ADBE (Adobe)

 - Adobe (ADBE) is a leading software company known for creative and document tools (Photoshop, Illustrator, Acrobat, Creative Cloud) and is considered a large-cap growth stock with strong recurring revenue from subscriptions.

 - https://www.kaggle.com/borismarjanovic/datasets

 ### 1st Commit

  - Small Flask API (`app/data.py`) that reads HTML table(s) from
	 `C:\Users\avram\OneDrive\Desktop\Bloomtech TRG\TRG Week 44\adbe.us.txt` and serves them as HTML or JSON. Run with a virtualenv and `python .\\app\\data.py`.

 ### 2nd Commit

 - The date of the data starts at 1986-08-14, and ends at 2017-11-10.

- Dropped the `OpenInt` column (not needed here) and split the main dataframe into three time-based objects (early / mid / recent) by terciles of the date range to capture regime changes over long history and make focused comparisons; implemented parsing and a `/tables/split` endpoint that returns these parts as JSON.

 ### 3rd Commit

- Added Bollinger Bands calculation and a `/tables/bbands` route that returns a PNG with three subplots visualizing bands for the early / mid / recent data splits to compare volatility and trend behavior across periods.

 ### 4th Commit

- Added MACD calculation and a `/tables/macd` route that returns a PNG visualizing price and MACD (MACD line, signal, histogram) for the early / mid / recent splits to assess momentum across periods.

 ### 5th Commit
- Added RSI calculation and a `/tables/rsi` route that returns a PNG visualizing RSI (with 30/70 thresholds) alongside price for early / mid / recent splits to identify overbought/oversold regimes.

### Summary

- This project provides a small Flask API that loads historical Adobe (ADBE) price data, normalizes it (drops unused columns and parses dates), and splits the series into three time-based slices for analysis. It implements technical indicators and visualizations — Bollinger Bands, MACD, and RSI — each exposed as PNG endpoints to compare volatility, momentum, and overbought/oversold regimes across early, mid, and recent periods. The goal is to make exploratory technical analysis repeatable and programmatic so you can quickly inspect regime changes and test indicator-based hypotheses on consistent time slices. The endpoints also support basic parameterization (window sizes, multipliers) to experiment with different indicator settings.