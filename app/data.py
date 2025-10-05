from flask import Flask, Response, jsonify, request
import pandas as pd
import os
from typing import List
import io
import matplotlib
# Use a non-interactive backend suitable for servers
matplotlib.use("Agg")
import matplotlib.pyplot as plt

app = Flask(__name__)

# Absolute path to the file containing HTML table(s)
DATA_FILE_PATH = r"C:\Users\avram\OneDrive\Desktop\Bloomtech TRG\TRG Week 44\adbe.us.txt"


def read_tables_from_file(path: str) -> List[pd.DataFrame]:
	"""Read tables from a file and return a list of DataFrames.

	Detection logic:
	- If the file contains HTML table tags (<table>), use pandas.read_html.
	- Otherwise, try reading it as CSV with pandas.read_csv.

	Returns a list of DataFrames to keep the same calling convention as before.
	"""
	if not os.path.isfile(path):
		raise FileNotFoundError(f"File not found: {path}")

	with open(path, "r", encoding="utf-8", errors="ignore") as f:
		# Read a sample (not the entire file) to detect format quickly
		sample = f.read(8192)
		f.seek(0)

		# If HTML table tag appears in the sample, parse as HTML
		if "<table" in sample.lower():
			content = f.read()
			tables = pd.read_html(content, flavor="bs4")
			return tables

		# Otherwise, try CSV. We'll use pandas.read_csv on the full file.
		try:
			df = pd.read_csv(f)

			# Normalize columns: drop OpenInt if present (not needed for this analysis)
			if "OpenInt" in df.columns:
				df = df.drop(columns=["OpenInt"])

			# Parse Date column if present
			if "Date" in df.columns:
				df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
				df = df.sort_values("Date").reset_index(drop=True)

			return [df]
		except Exception as csv_err:
			# Fall back to read_html as a last resort
			f.seek(0)
			content = f.read()
			try:
				tables = pd.read_html(content, flavor="bs4")
				return tables
			except Exception:
				# Raise original CSV error to indicate failure to parse
				raise csv_err


@app.route("/", methods=["GET"])
def index():
	return (
		"<h3>Data API</h3>"
		"<p>Endpoints:</p>"
		"<ul>"
		"<li>/tables - return combined HTML of all tables</li>"
		"<li>/tables/json - return JSON array of tables</li>"
		"</ul>"
	)


@app.route("/health", methods=["GET"])
def health():
	return jsonify({"status": "ok"})


@app.route("/tables", methods=["GET"])
def tables_html():
	"""Return the HTML representation of tables found in the file.

	Optional query param `table` (0-based index) to return a single table.
	"""
	try:
		tables = read_tables_from_file(DATA_FILE_PATH)
	except FileNotFoundError as e:
		return Response(str(e), status=404)
	except ValueError as e:
		# pandas.read_html raises ValueError if no tables found
		return Response(f"No tables found in file: {DATA_FILE_PATH}", status=404)
	except Exception as e:
		return Response(f"Error reading tables: {e}", status=500)

	table_idx = request.args.get("table", default=None, type=int)

	if table_idx is not None:
		if table_idx < 0 or table_idx >= len(tables):
			return Response("table index out of range", status=400)
		html = tables[table_idx].to_html(index=False, border=1)
		return Response(html, mimetype="text/html")

	# Combine all tables into a single HTML response
	html_parts = []
	for i, df in enumerate(tables):
		html_parts.append(f"<h4>Table {i}</h4>")
		html_parts.append(df.to_html(index=False, border=1))

	combined = "\n".join(html_parts)
	return Response(combined, mimetype="text/html")


@app.route("/tables/json", methods=["GET"])
def tables_json():
	"""Return JSON array of tables. Each table is an array of objects (records).

	Optional query param `table` to return a single table as JSON.
	"""
	try:
		tables = read_tables_from_file(DATA_FILE_PATH)
	except FileNotFoundError as e:
		return jsonify({"error": str(e)}), 404
	except ValueError:
		return jsonify({"error": "No tables found in file"}), 404
	except Exception as e:
		return jsonify({"error": f"Error reading tables: {e}"}), 500

	table_idx = request.args.get("table", default=None, type=int)

	if table_idx is not None:
		if table_idx < 0 or table_idx >= len(tables):
			return jsonify({"error": "table index out of range"}), 400
		return jsonify(tables[table_idx].to_dict(orient="records"))

	return jsonify([df.to_dict(orient="records") for df in tables])


if __name__ == "__main__":
	# Development server
	app.run(host="127.0.0.1", port=5000, debug=True)


def split_into_terciles(df: pd.DataFrame):
	"""Split a time-sorted dataframe into three roughly equal time ranges.

	Returns a dict with keys 'early', 'mid', 'recent'. If Date is missing,
	splits by row counts.
	"""
	if df.empty:
		return {"early": df, "mid": df, "recent": df}

	if "Date" in df.columns and pd.api.types.is_datetime64_any_dtype(df["Date"]):
		# Compute date-based cut points at 1/3 and 2/3 of the date range
		dates = df["Date"].dropna().sort_values()
		if dates.empty:
			# fallback to equal splits by rows
			n = len(df)
			return {
				"early": df.iloc[: n // 3].copy(),
				"mid": df.iloc[n // 3 : (2 * n) // 3].copy(),
				"recent": df.iloc[(2 * n) // 3 :].copy(),
			}

		t1 = dates.iloc[max(0, len(dates) // 3 - 1)]
		t2 = dates.iloc[max(0, (2 * len(dates)) // 3 - 1)]

		early = df[df["Date"] <= t1].copy()
		mid = df[(df["Date"] > t1) & (df["Date"] <= t2)].copy()
		recent = df[df["Date"] > t2].copy()
		return {"early": early, "mid": mid, "recent": recent}

	# If no Date column, split by row counts
	n = len(df)
	return {
		"early": df.iloc[: n // 3].copy(),
		"mid": df.iloc[n // 3 : (2 * n) // 3].copy(),
		"recent": df.iloc[(2 * n) // 3 :].copy(),
	}


@app.route("/tables/split", methods=["GET"])
def tables_split_json():
	"""Return JSON of the full dataframe and its three time-based splits.

	Query param `part` can be 'all' (default), 'early', 'mid', or 'recent'.
	"""
	try:
		tables = read_tables_from_file(DATA_FILE_PATH)
	except FileNotFoundError as e:
		return jsonify({"error": str(e)}), 404
	except Exception as e:
		return jsonify({"error": f"Error reading tables: {e}"}), 500

	# We expect the CSV to be returned as a single DataFrame
	if not tables:
		return jsonify({"error": "No data found"}), 404

	df = tables[0]
	splits = split_into_terciles(df)

	part = request.args.get("part", default="all")
	if part == "all":
		return jsonify({
			"all": df.to_dict(orient="records"),
			"early": splits["early"].to_dict(orient="records"),
			"mid": splits["mid"].to_dict(orient="records"),
			"recent": splits["recent"].to_dict(orient="records"),
		})
	elif part in splits:
		return jsonify({part: splits[part].to_dict(orient="records")})
	else:
		return jsonify({"error": "unknown part"}), 400



def compute_bbands(df: pd.DataFrame, n: int = 20, k: float = 2.0) -> pd.DataFrame:
	"""Compute Bollinger Bands for a dataframe with a 'Close' column.

	Returns a copy of df with added columns: MA, Upper, Lower, PercentB, BandWidth
	"""
	df = df.copy()
	if "Close" not in df.columns:
		return df

	df["MA"] = df["Close"].rolling(window=n, min_periods=1).mean()
	df["Std"] = df["Close"].rolling(window=n, min_periods=1).std(ddof=0)
	df["Upper"] = df["MA"] + k * df["Std"]
	df["Lower"] = df["MA"] - k * df["Std"]
	df["PercentB"] = (df["Close"] - df["Lower"]) / (df["Upper"] - df["Lower"])
	df["BandWidth"] = (df["Upper"] - df["Lower"]) / df["MA"]
	return df


@app.route("/tables/bbands", methods=["GET"])
def tables_bbands_png():
	"""Return a PNG image showing Bollinger Bands for early/mid/recent data.

	Optional query params: n (window), k (std multiplier)
	"""
	try:
		tables = read_tables_from_file(DATA_FILE_PATH)
	except FileNotFoundError as e:
		return jsonify({"error": str(e)}), 404
	except Exception as e:
		return jsonify({"error": f"Error reading tables: {e}"}), 500

	if not tables:
		return jsonify({"error": "No data found"}), 404

	df = tables[0]
	splits = split_into_terciles(df)

	# Params
	n = request.args.get("n", default=20, type=int)
	k = request.args.get("k", default=2.0, type=float)

	figs = []
	fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=False)
	parts = ["early", "mid", "recent"]
	for ax, part in zip(axes, parts):
		part_df = splits[part]
		if part_df.empty or "Close" not in part_df.columns:
			ax.text(0.5, 0.5, f"No data for {part}", ha="center", va="center")
			continue

		bb = compute_bbands(part_df, n=n, k=k)
		x = bb["Date"] if "Date" in bb.columns else range(len(bb))
		ax.plot(x, bb["Close"], label="Close", color="black")
		ax.plot(x, bb["MA"], label=f"MA({n})", color="blue")
		ax.plot(x, bb["Upper"], label="Upper", color="red", linestyle="--")
		ax.plot(x, bb["Lower"], label="Lower", color="green", linestyle="--")
		ax.set_title(f"Bollinger Bands - {part}")
		ax.legend(loc="best")

	plt.tight_layout()
	buf = io.BytesIO()
	fig.savefig(buf, format="png")
	plt.close(fig)
	buf.seek(0)
	return Response(buf.getvalue(), mimetype="image/png")


def compute_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9):
	"""Compute MACD, signal, and histogram for a dataframe with 'Close'.

	Returns a DataFrame with added columns 'MACD', 'Signal', 'Hist'.
	"""
	df = df.copy()
	if "Close" not in df.columns:
		return df

	ema_fast = df["Close"].ewm(span=fast, adjust=False).mean()
	ema_slow = df["Close"].ewm(span=slow, adjust=False).mean()
	macd = ema_fast - ema_slow
	signal_line = macd.ewm(span=signal, adjust=False).mean()
	hist = macd - signal_line

	df["MACD"] = macd
	df["Signal"] = signal_line
	df["Hist"] = hist
	return df


@app.route("/tables/macd", methods=["GET"])
def tables_macd_png():
	"""Return a PNG showing MACD plots for early/mid/recent splits.

	Query params: fast, slow, signal (defaults 12,26,9)
	"""
	try:
		tables = read_tables_from_file(DATA_FILE_PATH)
	except FileNotFoundError as e:
		return jsonify({"error": str(e)}), 404
	except Exception as e:
		return jsonify({"error": f"Error reading tables: {e}"}), 500

	if not tables:
		return jsonify({"error": "No data found"}), 404

	df = tables[0]
	splits = split_into_terciles(df)

	fast = request.args.get("fast", default=12, type=int)
	slow = request.args.get("slow", default=26, type=int)
	signal = request.args.get("signal", default=9, type=int)

	fig, axes = plt.subplots(3, 2, figsize=(12, 10), gridspec_kw={"width_ratios": [3, 1]})
	parts = ["early", "mid", "recent"]
	for row, part in enumerate(parts):
		part_df = splits[part]
		ax_price = axes[row][0]
		ax_macd = axes[row][1]

		if part_df.empty or "Close" not in part_df.columns:
			ax_price.text(0.5, 0.5, f"No data for {part}", ha="center", va="center")
			ax_macd.axis("off")
			continue

		macd_df = compute_macd(part_df, fast=fast, slow=slow, signal=signal)
		x = macd_df["Date"] if "Date" in macd_df.columns else range(len(macd_df))

		# Price plot on left
		ax_price.plot(x, macd_df["Close"], color="black")
		ax_price.set_title(f"Price - {part}")

		# MACD on right: MACD, Signal, Hist
		ax_macd.plot(x, macd_df["MACD"], label="MACD", color="blue")
		ax_macd.plot(x, macd_df["Signal"], label="Signal", color="red")
		ax_macd.bar(x, macd_df["Hist"], label="Hist", color="gray", alpha=0.6)
		ax_macd.set_title(f"MACD - {part}")
		ax_macd.legend()

	plt.tight_layout()
	buf = io.BytesIO()
	fig.savefig(buf, format="png")
	plt.close(fig)
	buf.seek(0)
	return Response(buf.getvalue(), mimetype="image/png")


