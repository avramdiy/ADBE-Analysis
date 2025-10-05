from flask import Flask, Response, jsonify, request
import pandas as pd
import os
from typing import List

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


