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

 ### 4th Commit

 ### 5th Commit